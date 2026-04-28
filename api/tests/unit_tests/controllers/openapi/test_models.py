from controllers.openapi._models import MessageMetadata, UsageInfo


def test_usage_info_defaults_zero():
    u = UsageInfo()
    assert u.prompt_tokens == 0
    assert u.completion_tokens == 0
    assert u.total_tokens == 0


def test_message_metadata_accepts_partial():
    m = MessageMetadata(usage=UsageInfo(total_tokens=10))
    assert m.usage.total_tokens == 10
    assert m.retriever_resources == []
