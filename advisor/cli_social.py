"""CLI commands for multi-platform social content (LinkedIn, Reddit, Twitter, copy research, digests)."""

from __future__ import annotations

import click

from advisor.pipeline_social import (
    create_linkedin_draft,
    create_reddit_draft,
    create_twitter_draft,
    run_async,
    run_copy_research_save,
    run_daily_digest_save,
)


@click.group()
def social() -> None:
    """Multi-platform social content commands."""


@social.command()
@click.option(
    "--platform",
    type=click.Choice(["linkedin", "reddit", "twitter", "all"]),
    default="linkedin",
    show_default=True,
)
@click.option("--topic", default="", help="Optional topic to focus on.")
@click.option("--subreddit", default="", help="Reddit only: hint for target subreddit.")
@click.option(
    "--allow-self-promo",
    is_flag=True,
    default=False,
    help="Reddit only: allow promotional tone (NOT recommended).",
)
@click.option("--thread", is_flag=True, default=False, help="Twitter only: build a thread.")
def draft(
    platform: str,
    topic: str,
    subreddit: str,
    allow_self_promo: bool,
    thread: bool,
) -> None:
    """Generate a draft for the chosen platform(s)."""
    targets = ["linkedin", "reddit", "twitter"] if platform == "all" else [platform]
    for plat in targets:
        click.echo(f"\n🚀 Generating {plat} draft...")
        if plat == "linkedin":
            d = run_async(create_linkedin_draft(topic))
            if d:
                click.echo(f"✅ {d.id}: {d.hook}")
            else:
                click.echo("❌ LinkedIn draft failed.")
        elif plat == "reddit":
            r = run_async(
                create_reddit_draft(
                    topic, allow_self_promo=allow_self_promo, subreddit_hint=subreddit
                )
            )
            if r:
                d, post = r
                click.echo(f"✅ {d.id}: r/{post.subreddit} — {post.title}")
                click.echo(f"   self_promo_level={post.self_promo_level} type={post.post_type}")
            else:
                click.echo("❌ Reddit draft failed.")
        elif plat == "twitter":
            t = run_async(create_twitter_draft(topic, as_thread=thread))
            if t:
                d, post = t
                count = len(post.thread) if post.thread else 1
                click.echo(f"✅ {d.id}: {post.text[:80]}... ({count} tweet(s))")
            else:
                click.echo("❌ Twitter draft failed.")


@social.command("copy-research")
@click.option("--niche", required=True, help="Niche to research, e.g. 'AI engineering'.")
@click.option(
    "--platforms",
    default="linkedin,reddit,twitter",
    show_default=True,
    help="Comma-separated platforms.",
)
def copy_research_cmd(niche: str, platforms: str) -> None:
    """Research successful post patterns across platforms."""
    plats = [p.strip() for p in platforms.split(",") if p.strip()]
    click.echo(f"🔍 Researching '{niche}' on {plats}...")
    result = run_async(run_copy_research_save(niche, plats))
    if not result:
        click.echo("❌ Copy research failed.")
        return
    analysis_id, analysis = result
    click.echo(f"✅ Analysis saved id={analysis_id}")
    click.echo(f"   Patterns: {len(analysis.patterns)}, Examples: {len(analysis.examples)}")
    for pattern in analysis.patterns[:5]:
        click.echo(f"   • [{pattern.platform}] {pattern.name}: {pattern.description[:80]}")


@social.command()
@click.option("--topic", default="", help="Optional extra topic to weave into the digest.")
def digest(topic: str) -> None:
    """Run the daily digest: scan GitHub activity and propose 3-5 posts."""
    click.echo("📰 Running daily digest...")
    result = run_async(run_daily_digest_save(extra_topic=topic))
    if not result:
        click.echo("❌ Digest failed.")
        return
    click.echo(f"✅ {len(result.proposals)} proposals saved")
    click.echo(f"   Notes: {result.notes[:160]}")
    for p in result.proposals:
        marker = f"r/{p.suggested_subreddit}" if p.platform == "reddit" else p.platform
        click.echo(f"   • [{marker}] ({p.confidence:.2f}) {p.headline}")


@social.command("list")
@click.option(
    "--status",
    type=click.Choice(["pending", "approved", "rejected", "all"]),
    default="pending",
    show_default=True,
)
@click.option(
    "--platform",
    type=click.Choice(["linkedin", "reddit", "twitter", "all"]),
    default="all",
    show_default=True,
)
def list_cmd(status: str, platform: str) -> None:
    """List drafts filtered by status and platform."""
    from advisor.db import PostsDB

    db = PostsDB()
    try:
        plat = "" if platform == "all" else platform
        statuses = ["pending", "approved", "rejected"] if status == "all" else [status]
        posts: list = []
        for s in statuses:
            posts.extend(db.list_by_status(s, plat))
        if not posts:
            click.echo("No matching posts.")
            return
        icons = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
        for p in posts:
            click.echo(f"{icons.get(str(p['status']), '❓')} [{p['platform']}] {p['id']} — {str(p['hook'])[:80]}")
            if p["platform"] == "reddit" and p["reddit_subreddit"]:
                click.echo(f"   r/{p['reddit_subreddit']} type={p['reddit_post_type']}")
    finally:
        db.close()


@social.command()
@click.argument("post_id")
def approve(post_id: str) -> None:
    """Approve a draft by ID."""
    from advisor.db import PostsDB

    db = PostsDB()
    try:
        ok = db.approve(post_id)
        click.echo("✅ Approved" if ok else "❌ Not found")
    finally:
        db.close()


@social.command()
@click.argument("post_id")
def reject(post_id: str) -> None:
    """Reject a draft by ID."""
    from advisor.db import PostsDB

    db = PostsDB()
    try:
        ok = db.reject(post_id)
        click.echo("✅ Rejected" if ok else "❌ Not found")
    finally:
        db.close()


@social.command("proposals")
@click.option(
    "--status",
    type=click.Choice(["pending", "approved", "rejected"]),
    default="pending",
    show_default=True,
)
def proposals_cmd(status: str) -> None:
    """List daily-digest content proposals."""
    from advisor.db import PostsDB

    db = PostsDB()
    try:
        rows = db.list_proposals(status)
        if not rows:
            click.echo("No proposals.")
            return
        for r in rows:
            sub = f" r/{r['suggested_subreddit']}" if r["suggested_subreddit"] else ""
            click.echo(
                f"[{r['platform']}{sub}] {r['id']} ({r['confidence']:.2f}) — {r['headline']}"
            )
            click.echo(f"   why: {r['reasoning'][:160]}")
    finally:
        db.close()


@social.command("analyses")
def analyses_cmd() -> None:
    """List stored copy analyses."""
    from advisor.db import PostsDB

    db = PostsDB()
    try:
        rows = db.list_copy_analyses()
        if not rows:
            click.echo("No analyses.")
            return
        for r in rows:
            click.echo(f"{r['id']} — {r['niche']} [{r['platforms']}] @ {r['created_at']}")
    finally:
        db.close()
