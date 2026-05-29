from publisher.douyin_message import conversation_id_from_parts, normalize_avatar_url


def test_normalize_avatar_url_adds_scheme():
    assert normalize_avatar_url("//p11.douyinpic.com/a.jpeg") == "https://p11.douyinpic.com/a.jpeg"


def test_normalize_avatar_url_keeps_absolute_url():
    assert normalize_avatar_url("https://p11.douyinpic.com/a.jpeg") == "https://p11.douyinpic.com/a.jpeg"


def test_conversation_id_uses_avatar_filename_without_query():
    cid = conversation_id_from_parts(
        "高栋栋",
        "https://p11.douyinpic.com/aweme/100x100/aweme-avatar/avatar_hash.jpeg?from=2956013662",
    )
    assert cid == "高栋栋_avatar_hash.jpeg"


def test_conversation_id_falls_back_to_name():
    assert conversation_id_from_parts("水球泡", "") == "水球泡"
