import asyncio
import base64

from flexus_client_kit import ckit_bot_install
from flexus_client_kit import ckit_client
from flexus_client_kit import ckit_cloudtool
from flexus_client_kit import ckit_integrations_db

from flexus_simple_bots import prompts_common
from flexus_my_bots.redditbot import redditbot_bot
from flexus_my_bots.redditbot import redditbot_prompts

SETUP_SCHEMA = [
    {
        "bs_name": "reddit_client_id",
        "bs_type": "string_short",
        "bs_default": "",
        "bs_group": "Reddit API",
        "bs_order": 1,
        "bs_importance": 1,
        "bs_description": (
            "Your Reddit app's client ID. "
            "Create one at https://www.reddit.com/prefs/apps \u2014 choose 'script' type."
        ),
    },
    {
        "bs_name": "reddit_client_secret",
        "bs_type": "string_short",
        "bs_default": "",
        "bs_group": "Reddit API",
        "bs_order": 2,
        "bs_importance": 1,
        "bs_description": "Your Reddit app's client secret (shown after creating the app).",
    },
    {
        "bs_name": "reddit_user_agent",
        "bs_type": "string_short",
        "bs_default": "refact-reddit-signals/1.0",
        "bs_group": "Reddit API",
        "bs_order": 3,
        "bs_importance": 0,
        "bs_description": "Short string identifying your app to Reddit's API. Default is fine.",
    },
    {
        "bs_name": "subreddits",
        "bs_type": "string_short",
        "bs_default": "programming+SoftwareEngineering+AskProgramming",
        "bs_group": "Monitoring",
        "bs_order": 4,
        "bs_importance": 0,
        "bs_description": (
            "Plus-separated list of subreddits to monitor. "
            "Example: programming+SoftwareEngineering+AskProgramming"
        ),
    },
]

TOOL_NAMESET = {t.name for t in redditbot_bot.TOOLS}

EXPERTS = [
    ("default", ckit_bot_install.FMarketplaceExpertInput(
        fexp_system_prompt=redditbot_prompts.redditbot_default_prompt,
        fexp_python_kernel="",
        fexp_allow_tools=",".join(
            TOOL_NAMESET | ckit_cloudtool.CLOUDTOOLS_SAFE
        ),
        fexp_nature="NATURE_AUTONOMOUS",
        fexp_inactivity_timeout=3600,
        fexp_description=(
            "Monitors Reddit weekly, analyzes posts for Refact.ai signals, "
            "and saves a structured report to the Reports section."
        ),
    )),
    ("setup", ckit_bot_install.FMarketplaceExpertInput(
        fexp_system_prompt=redditbot_prompts.redditbot_setup_prompt,
        fexp_python_kernel="",
        fexp_allow_tools=",".join(
            {"verify_reddit_credentials"} | ckit_cloudtool.CLOUDTOOLS_SAFE
        ),
        fexp_nature="NATURE_INTERACTIVE",
        fexp_description="Guides the user through configuring Reddit API credentials.",
    )),
]


async def install(
    client: ckit_client.FlexusClient,
    bot_name: str,
    bot_version: str,
    tools: list[ckit_cloudtool.CloudTool],
):
    try:
        pic_big = base64.b64encode(
            (redditbot_bot.BOT_ROOTDIR / "redditbot-1024x1536.webp").read_bytes()
        ).decode("ascii")
        pic_small = base64.b64encode(
            (redditbot_bot.BOT_ROOTDIR / "redditbot-256x256.webp").read_bytes()
        ).decode("ascii")
    except FileNotFoundError:
        pic_big = ""
        pic_small = ""

    await ckit_bot_install.marketplace_upsert_dev_bot(
        client,
        ws_id=client.ws_id,
        marketable_name=bot_name,
        marketable_version=bot_version,
        marketable_accent_color="#FF4500",
        marketable_title1="Reddit Signal Monitor",
        marketable_title2="Weekly Reddit intelligence reports for Refact.ai",
        marketable_author="Refact.ai",
        marketable_occupation="Market Intelligence",
        marketable_description=(
            redditbot_bot.BOT_ROOTDIR / "README.md"
        ).read_text(),
        marketable_typical_group="Monitoring / Intelligence",
        marketable_github_repo="https://github.com/katrinmaikova/refact-reddit-signals",
        marketable_run_this="python -m flexus_my_bots.redditbot.redditbot_bot",
        marketable_setup_default=SETUP_SCHEMA,
        marketable_featured_actions=[
            {
                "feat_question": "Generate this week's Reddit signal report",
                "feat_expert": "default",
                "feat_depends_on_setup": ["reddit_client_id", "reddit_client_secret"],
            },
            {
                "feat_question": "Show me the latest report",
                "feat_expert": "default",
                "feat_depends_on_setup": [],
            },
        ],
        marketable_intro_message=(
            "Hi! I\u2019m your Reddit Signal Monitor for Refact.ai. "
            "Every Monday at 9:00 AM I automatically scan r/programming, "
            "r/SoftwareEngineering, and r/AskProgramming and save a structured "
            "signal report to the Reports section. "
            "You can also ask me to run a report right now."
        ),
        marketable_preferred_model_expensive="gpt-4o",
        marketable_preferred_model_cheap="gpt-4o-mini",
        marketable_experts=[
            (name, exp.filter_tools(tools)) for name, exp in EXPERTS
        ],
        add_integrations_into_expert_system_prompt=redditbot_bot.BOT_INTEGRATIONS,
        marketable_tags=["Reddit", "Monitoring", "Intelligence", "Refact"],
        marketable_picture_big_b64=pic_big,
        marketable_picture_small_b64=pic_small,
        marketable_schedule=[
            prompts_common.SCHED_TODO_5M | {
                "sched_when": "WEEKDAYS:MO/09:00",
                "sched_first_question": (
                    "It's Monday morning \u2014 time for the weekly Reddit signal report. "
                    "Fetch this week's top posts from all configured subreddits, analyze them "
                    "for Refact.ai signals, write the structured report, and save it to "
                    "/reports/reddit-signals/ using today's date in the filename."
                ),
                "sched_fexp_name": "default",
            },
        ],
    )


if __name__ == "__main__":
    client = ckit_client.FlexusClient("redditbot_install")
    asyncio.run(
        install(
            client,
            bot_name=redditbot_bot.BOT_NAME,
            bot_version=redditbot_bot.BOT_VERSION,
            tools=redditbot_bot.TOOLS,
        )
    )
