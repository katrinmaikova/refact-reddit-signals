import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from flexus_client_kit import ckit_bot_exec
from flexus_client_kit import ckit_client
from flexus_client_kit import ckit_cloudtool
from flexus_client_kit import ckit_integrations_db
from flexus_client_kit import ckit_shutdown

logger = logging.getLogger("redditbot")

BOT_NAME = "redditbot"
BOT_VERSION = "1.0.7"
BOT_ROOTDIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------

BOT_INTEGRATIONS: list[ckit_integrations_db.IntegrationRecord] = (
    ckit_integrations_db.static_integrations_load(
        BOT_ROOTDIR,
        allowlist=["flexus_policy_document"],
        builtin_skills=[],
    )
)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

FETCH_REDDIT_POSTS_TOOL = ckit_cloudtool.CloudTool(
    strict=True,
    name="fetch_reddit_posts",
    description=(
        "Fetch recent hot/top posts from the configured subreddits using the Reddit API. "
        "Returns a JSON list of posts with title, score, URL, and top comment."
    ),
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max posts per subreddit (default 25, max 100)",
            },
            "sort": {
                "type": "string",
                "enum": ["hot", "top", "new"],
                "description": "Sort order for posts",
            },
            "time_filter": {
                "type": ["string", "null"],
                "description": "Time window for 'top' sort: day, week, month, year, all. Pass null for hot/new.",
            },
        },
        "required": ["limit", "sort", "time_filter"],
        "additionalProperties": False,
    },
)

VERIFY_CREDENTIALS_TOOL = ckit_cloudtool.CloudTool(
    strict=True,
    name="verify_reddit_credentials",
    description="Verify that the Reddit API credentials are valid by making a test API call.",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
)

TOOLS = [
    FETCH_REDDIT_POSTS_TOOL,
    VERIFY_CREDENTIALS_TOOL,
    *[t for rec in BOT_INTEGRATIONS for t in rec.integr_tools],
]


# ---------------------------------------------------------------------------
# Fake data for scenarios
# ---------------------------------------------------------------------------

def _fake_posts() -> str:
    return json.dumps([
        {
            "subreddit": "r/programming",
            "title": "I've been using AI coding assistants for 6 months \u2014 honest review",
            "score": 1842,
            "url": "https://www.reddit.com/r/programming/comments/abc123",
            "num_comments": 312,
            "created_utc": "2026-04-01T10:00:00Z",
            "top_comment": "Switched to an open-weights model I can run locally. Privacy matters.",
        },
        {
            "subreddit": "r/SoftwareEngineering",
            "title": "AI pair programming tools comparison 2026",
            "score": 920,
            "url": "https://www.reddit.com/r/SoftwareEngineering/comments/def456",
            "num_comments": 178,
            "created_utc": "2026-04-02T14:30:00Z",
            "top_comment": "Anyone tried Refact.ai? Supports self-hosting which is huge for my company.",
        },
        {
            "subreddit": "r/AskProgramming",
            "title": "Best free AI code completion that works offline?",
            "score": 445,
            "url": "https://www.reddit.com/r/AskProgramming/comments/ghi789",
            "num_comments": 89,
            "created_utc": "2026-04-03T09:15:00Z",
            "top_comment": "Refact.ai has a self-hosted option. Works great with VS Code.",
        },
    ])


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def redditbot_main_loop(
    fclient: ckit_client.FlexusClient,
    rcx: ckit_bot_exec.RobotContext,
) -> None:
    from flexus_my_bots.redditbot import redditbot_install
    from flexus_client_kit.integrations import fi_pdoc

    setup = ckit_bot_exec.official_setup_mixing_procedure(
        redditbot_install.SETUP_SCHEMA, rcx.persona.persona_setup
    )
    integr_objects = await ckit_integrations_db.main_loop_integrations_init(
        BOT_INTEGRATIONS, rcx, setup
    )
    pdoc_integration: fi_pdoc.IntegrationPdoc = integr_objects["flexus_policy_document"]

    @rcx.on_tool_call(FETCH_REDDIT_POSTS_TOOL.name)
    async def toolcall_fetch_posts(
        toolcall: ckit_cloudtool.FCloudtoolCall,
        model_produced_args: Dict[str, Any],
    ) -> str:
        if rcx.running_test_scenario:
            return _fake_posts()

        reddit_client_id = setup.get("reddit_client_id", "").strip()
        reddit_client_secret = setup.get("reddit_client_secret", "").strip()
        if not reddit_client_id or not reddit_client_secret:
            return "Error: Reddit API credentials not configured. Please complete setup first."

        limit = model_produced_args.get("limit", 25)
        sort = model_produced_args.get("sort", "top")
        time_filter = model_produced_args.get("time_filter") or "week"
        subreddits_raw = setup.get(
            "subreddits", "programming+SoftwareEngineering+AskProgramming"
        )
        subreddit_list = [s.strip() for s in subreddits_raw.replace("+", ",").split(",") if s.strip()]

        try:
            import praw

            reddit = praw.Reddit(
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent=setup.get("reddit_user_agent", "refact-reddit-signals/1.0"),
            )

            results = []
            for sr_name in subreddit_list:
                sr = reddit.subreddit(sr_name)
                if sort == "top":
                    posts = sr.top(time_filter=time_filter, limit=limit)
                elif sort == "hot":
                    posts = sr.hot(limit=limit)
                else:
                    posts = sr.new(limit=limit)

                for post in posts:
                    top_comment = ""
                    try:
                        post.comments.replace_more(limit=0)
                        if post.comments:
                            top_comment = post.comments[0].body[:300]
                    except Exception:
                        pass

                    results.append({
                        "subreddit": f"r/{sr_name}",
                        "title": post.title,
                        "score": post.score,
                        "url": f"https://www.reddit.com{post.permalink}",
                        "num_comments": post.num_comments,
                        "created_utc": datetime.fromtimestamp(
                            post.created_utc, tz=timezone.utc
                        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "top_comment": top_comment,
                    })

            return json.dumps(results, ensure_ascii=False)
        except Exception as exc:
            logger.exception("fetch_reddit_posts failed")
            return f"Error fetching Reddit posts: {exc}"

    @rcx.on_tool_call(VERIFY_CREDENTIALS_TOOL.name)
    async def toolcall_verify_credentials(
        toolcall: ckit_cloudtool.FCloudtoolCall,
        model_produced_args: Dict[str, Any],
    ) -> str:
        if rcx.running_test_scenario:
            return "\u2705 Reddit credentials verified successfully (test mode)"

        reddit_client_id = setup.get("reddit_client_id", "").strip()
        reddit_client_secret = setup.get("reddit_client_secret", "").strip()
        if not reddit_client_id or not reddit_client_secret:
            return "\u274c Reddit credentials not configured. Please add your Reddit API client_id and client_secret."

        try:
            import praw

            reddit = praw.Reddit(
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent=setup.get("reddit_user_agent", "refact-reddit-signals/1.0"),
            )
            _ = reddit.subreddit("programming").title
            return "\u2705 Reddit credentials verified. Connected to Reddit API (read-only)."
        except Exception as exc:
            logger.exception("verify_credentials failed")
            return f"\u274c Reddit credential verification failed: {exc}"

    try:
        while not ckit_shutdown.shutdown_event.is_set():
            await rcx.unpark_collected_events(sleep_if_no_work=10.0)
    finally:
        logger.info("%s exit" % (rcx.persona.persona_id,))


def main():
    from flexus_my_bots.redditbot import redditbot_install

    scenario_fn = ckit_bot_exec.parse_bot_args()
    fclient = ckit_client.FlexusClient(
        ckit_client.bot_service_name(BOT_NAME, BOT_VERSION),
        endpoint="/v1/jailed-bot",
    )
    asyncio.run(
        ckit_bot_exec.run_bots_in_this_group(
            fclient,
            marketable_name=BOT_NAME,
            marketable_version_str=BOT_VERSION,
            bot_main_loop=redditbot_main_loop,
            inprocess_tools=TOOLS,
            scenario_fn=scenario_fn,
            install_func=redditbot_install.install,
        )
    )


if __name__ == "__main__":
    main()
