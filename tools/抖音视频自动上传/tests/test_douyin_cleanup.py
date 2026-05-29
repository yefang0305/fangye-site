from datetime import datetime, timedelta

from publisher.douyin_cleanup import (
    CleanupDecision,
    CleanupResult,
    DouyinCleanupRunner,
    WorkInfo,
    choose_cleanup_action,
    is_active_douyin_account,
    matches_retry_target,
    parse_count,
    parse_publish_time,
    parse_work_from_row_text,
)


def test_parse_count_handles_plain_commas_wan_and_dash():
    assert parse_count("834") == 834
    assert parse_count("1,234") == 1234
    assert parse_count("1.2万") == 12000
    assert parse_count("-") is None


def test_parse_publish_time_handles_douyin_timestamp():
    assert parse_publish_time("2026年05月21日 03:00") == datetime(2026, 5, 21, 3, 0)


def test_restricted_marker_deletes_even_when_metrics_and_time_are_missing():
    work = WorkInfo(
        title="你努不努力都是命中注定的",
        publish_time=None,
        plays=None,
        likes=None,
        has_detail_link=True,
    )

    decision = choose_cleanup_action(work, now=datetime(2026, 5, 26, 12, 0))

    assert decision == CleanupDecision(True, "限流查看详情")


def test_fresh_work_is_skipped_even_when_metrics_are_low():
    now = datetime(2026, 5, 26, 12, 0)
    work = WorkInfo(
        title="刚发的新作品",
        publish_time=now - timedelta(hours=23, minutes=59),
        plays=1,
        likes=0,
        has_detail_link=False,
    )

    decision = choose_cleanup_action(work, now=now)

    assert decision == CleanupDecision(False, "24小时内跳过")


def test_old_low_play_and_low_like_work_is_deleted():
    now = datetime(2026, 5, 26, 12, 0)
    work = WorkInfo(
        title="低效作品",
        publish_time=now - timedelta(days=2),
        plays=999,
        likes=29,
        has_detail_link=False,
    )

    decision = choose_cleanup_action(work, now=now)

    assert decision == CleanupDecision(True, "低播放低点赞")


def test_missing_metrics_do_not_match_low_metric_rule():
    now = datetime(2026, 5, 26, 12, 0)
    work = WorkInfo(
        title="指标缺失",
        publish_time=now - timedelta(days=2),
        plays=None,
        likes=None,
        has_detail_link=False,
    )

    decision = choose_cleanup_action(work, now=now)

    assert decision == CleanupDecision(False, "指标缺失跳过")


def test_only_active_douyin_accounts_are_selected():
    assert is_active_douyin_account({"platform": "douyin", "is_active": 1}) is True
    assert is_active_douyin_account({"platform": "douyin", "is_active": 0}) is False
    assert is_active_douyin_account({"platform": "kuaishou", "is_active": 1}) is False


def test_parse_work_from_row_text_extracts_title_time_metrics_and_detail_marker():
    text = "\n".join(
        [
            "人越稳越淡越能吸引到对的人",
            "2026年05月21日 03:00",
            "限制自己可见    查看详情",
            "播放",
            "834",
            "点赞",
            "52",
            "评论",
            "1",
            "分享",
            "2",
            "删除作品",
        ]
    )

    parsed = parse_work_from_row_text(text)

    assert parsed.title == "人越稳越淡越能吸引到对的人"
    assert parsed.publish_time == datetime(2026, 5, 21, 3, 0)
    assert parsed.publish_time_text == "2026年05月21日 03:00"
    assert parsed.plays == 834
    assert parsed.plays_text == "834"
    assert parsed.likes == 52
    assert parsed.likes_text == "52"
    assert parsed.has_detail_link is True


def test_parse_work_from_row_text_ignores_thumbnail_duration_before_title():
    text = "\n".join(
        [
            "01:05",
            "你努不努力都是命中注定的",
            "2026年05月23日 03:00",
            "限制自己可见",
            "查看详情",
            "播放",
            "-",
            "点赞",
            "-",
            "删除作品",
        ]
    )

    parsed = parse_work_from_row_text(text)

    assert parsed.title == "你努不努力都是命中注定的"


def test_matches_retry_target_uses_title_and_publish_time_when_available():
    work = WorkInfo(
        title="低效作品",
        publish_time=datetime(2026, 5, 21, 3, 0),
        plays=10,
        likes=1,
        has_detail_link=False,
    )

    assert matches_retry_target(work, "低效作品", "2026年05月21日 03:00") is True
    assert matches_retry_target(work, "其他作品", "2026年05月21日 03:00") is False
    assert matches_retry_target(work, "低效作品", "2026年05月22日 03:00") is False


def test_matches_retry_target_allows_account_level_retry_without_title():
    work = WorkInfo(
        title="任意作品",
        publish_time=datetime(2026, 5, 21, 3, 0),
        plays=10,
        likes=1,
        has_detail_link=False,
    )

    assert matches_retry_target(work, "", "") is True


def test_runner_processes_only_active_douyin_accounts_in_order():
    accounts = [
        {"id": 1, "platform": "douyin", "is_active": 1, "display_name": "a1"},
        {"id": 2, "platform": "kuaishou", "is_active": 1, "display_name": "ks"},
        {"id": 3, "platform": "douyin", "is_active": 0, "display_name": "off"},
        {"id": 4, "platform": "douyin", "is_active": 1, "display_name": "a4"},
    ]
    seen = []

    def fake_cleaner(account, stop_requested):
        seen.append(account["id"])
        return [
            CleanupResult(
                account_id=account["id"],
                account_name=account["display_name"],
                title=f"work-{account['id']}",
                publish_time="",
                plays="",
                likes="",
                reason="数据达标跳过",
                status="跳过",
                detail="",
            )
        ]

    runner = DouyinCleanupRunner(accounts, clean_account=fake_cleaner)

    results = list(runner.run())

    assert seen == [1, 4]
    assert [r.title for r in results] == ["work-1", "work-4"]


def test_runner_stops_before_next_account_when_stop_is_requested():
    accounts = [
        {"id": 1, "platform": "douyin", "is_active": 1, "display_name": "a1"},
        {"id": 2, "platform": "douyin", "is_active": 1, "display_name": "a2"},
    ]
    calls = 0

    def fake_cleaner(account, stop_requested):
        nonlocal calls
        calls += 1
        return [
            CleanupResult(
                account_id=account["id"],
                account_name=account["display_name"],
                title="",
                publish_time="",
                plays="",
                likes="",
                reason="",
                status="账号完成",
                detail="",
            )
        ]

    runner = DouyinCleanupRunner(accounts, clean_account=fake_cleaner, stop_requested=lambda: calls >= 1)

    results = list(runner.run())

    assert calls == 1
    assert len(results) == 1
