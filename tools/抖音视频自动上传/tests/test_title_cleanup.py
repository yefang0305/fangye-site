"""Title cleanup: strip _\\d+$ suffix from filename stem before publishing."""
from publisher.queue import _clean_title


def test_strip_single_digit_suffix():
    assert _clean_title("养生秘诀_3") == "养生秘诀"


def test_strip_multi_digit_suffix():
    assert _clean_title("video_001") == "video"


def test_keep_underscore_when_no_digits():
    assert _clean_title("name_") == "name_"


def test_keep_when_digits_in_middle():
    assert _clean_title("a_b_2") == "a_b"   # only trailing _\d+ removed


def test_keep_unchanged_when_no_suffix():
    assert _clean_title("nochange") == "nochange"


def test_idempotent():
    assert _clean_title(_clean_title("title_5")) == "title"


def test_empty_string():
    assert _clean_title("") == ""
