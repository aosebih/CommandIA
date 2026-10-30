"""Conversation state machine, extraction sanitizing and escalation."""
from tests.conftest import extraction_payload


def test_invalid_phone_does_not_discard_other_fields(make_service):
    """A malformed phone must not throw away the rest of the order."""
    service = make_service([
        extraction_payload(
            customer_name="Ahmed",
            phone_number="12345",
            wilaya_code=16,
            address="Rue X",
        )
    ])
    result = service.process_message(user_message="Ismi Ahmed 12345")

    assert result.get("error") is None
    assert result["collected_fields"]["customer_name"] == "Ahmed"
    assert result["collected_fields"]["wilaya_code"] == 16
    assert result["collected_fields"]["address"] == "Rue X"
    assert "phone_number" in result["missing_fields"]


def test_phone_is_normalized_to_local_format(make_service):
    service = make_service([
        extraction_payload(customer_name="Ahmed", phone_number="+213 550 12 34 56")
    ])
    result = service.process_message(user_message="Numero 0550123456")
    assert result["collected_fields"]["phone_number"] == "0550123456"


def test_invalid_wilaya_and_delivery_type_are_dropped(make_service):
    service = make_service([
        extraction_payload(
            customer_name="Ahmed",
            wilaya_code=99,
            delivery_type="home",
        )
    ])
    result = service.process_message(user_message="Ana men Alger")
    assert "wilaya_code" not in result["collected_fields"]
    assert "wilaya_code" in result["missing_fields"]
    # The delivery type is repaired to the enum value, not dropped.
    assert result["collected_fields"]["delivery_type"] == "HOME"


def test_full_booking_reaches_confirmation(make_service):
    payloads = [
        extraction_payload(),
        extraction_payload(customer_name="Ahmed Benali"),
        extraction_payload(phone_number="0550123456"),
        extraction_payload(wilaya_code=16),
        extraction_payload(delivery_type="HOME"),
        extraction_payload(address="Rue Didouche, Alger Centre", total_price_da=4000),
    ]
    service = make_service(payloads)
    conversation_id = None
    messages = [
        "Rani bghit nchri had produit",
        "Ismi Ahmed Benali",
        "0550123456",
        "Ana men Alger",
        "Home delivery",
        "Rue Didouche, Alger Centre",
    ]
    for message in messages:
        result = service.process_message(user_message=message, conversation_id=conversation_id)
        conversation_id = result["conversation_id"]

    assert result["state"] == "CONFIRMATION"
    assert result["missing_fields"] == []


def test_confirmation_requires_explicit_yes(make_service):
    service = make_service([
        extraction_payload(
            customer_name="Ahmed Benali",
            phone_number="0550123456",
            wilaya_code=16,
            delivery_type="HOME",
            address="Rue X",
            order_status="CONFIRMED",
        )
    ])
    result = service.process_message(user_message="hej kifach")
    # The model claiming CONFIRMED must not be trusted before confirmation.
    assert result["extracted_data"]["order_status"] == "PENDING_CONFIRMATION"


def test_escalation_after_three_failed_attempts(make_service):
    service = make_service([extraction_payload(customer_name="Ahmed Benali")]
                           + [extraction_payload() for _ in range(4)])
    conversation_id = None
    states = []
    for message in ["Rani bghit nchri", "Ismi Ahmed Benali", "???", "???", "???"]:
        result = service.process_message(user_message=message, conversation_id=conversation_id)
        conversation_id = result["conversation_id"]
        states.append(result["state"])

    assert states[-1] == "ESCALATION"
    assert result["extracted_data"]["order_status"] == "REQUIRES_HUMAN"


def test_reply_is_always_present(make_service):
    service = make_service([extraction_payload(reply="Salam!")])
    result = service.process_message(user_message="Salam")
    assert result["reply_to_customer"] == "Salam!"
    assert result.get("error") is None


def test_price_question_stays_in_inquiry(make_service):
    service = make_service([extraction_payload()])
    result = service.process_message(user_message="Bonjour, quel est le prix de cette chemise ?")
    assert result["state"] == "INQUIRY"


def test_purchase_intent_is_detected_in_every_language(make_service):
    for message in [
        "Rani bghit nchri had produit",
        "je souhaite commander un article",
        "3tini had l3iba",
        "I want to order a product",
    ]:
        service = make_service([extraction_payload()])
        result = service.process_message(user_message=message)
        assert result["state"] == "ORDER_INTENT", message


def test_state_never_regresses_to_inquiry(make_service):
    """A garbled turn must not send an open order back to the inquiry state."""
    service = make_service([extraction_payload() for _ in range(3)])
    conversation_id = None
    states = []
    for message in ["Rani bghit nchri", "???", "???"]:
        result = service.process_message(user_message=message, conversation_id=conversation_id)
        conversation_id = result["conversation_id"]
        states.append(result["state"])

    assert states == ["ORDER_INTENT", "ORDER_INTENT", "ORDER_INTENT"]


def test_failed_attempts_still_escalate_without_new_data(make_service):
    service = make_service([extraction_payload() for _ in range(5)])
    conversation_id = None
    states = []
    for message in ["Rani bghit nchri", "???", "???", "???", "???"]:
        result = service.process_message(user_message=message, conversation_id=conversation_id)
        conversation_id = result["conversation_id"]
        states.append(result["state"])

    assert states[-1] == "ESCALATION"
    assert result["extracted_data"]["order_status"] == "REQUIRES_HUMAN"
