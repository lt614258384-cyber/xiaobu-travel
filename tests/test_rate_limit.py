from middleware.rate_limit import check_rate_limit, check_user_rate_limit


def test_ip_rate_limit_allows_within_limit():
    for i in range(5):
        assert check_rate_limit(f"192.168.1.{i}", "test", 5, 60) is True


def test_ip_rate_limit_blocks_when_exceeded():
    ip = "10.0.0.1"
    for _ in range(5):
        assert check_rate_limit(ip, "test", 5, 60) is True
    assert check_rate_limit(ip, "test", 5, 60) is False


def test_user_rate_limit_blocks_when_exceeded():
    for _ in range(3):
        assert check_user_rate_limit(42, "generate", 3, 86400) is True
    assert check_user_rate_limit(42, "generate", 3, 86400) is False
