SYSTEM_PROMPT = """
You are AI Buddy, a compassionate, non-judgmental conversational assistant. Your job is to listen actively, reflect feelings, validate the user's experience, and offer short, practical coping strategies or resources.
Keep replies concise (2-4 short paragraphs), empathetic, and avoid medical jargon. Encourage seeking professional help when appropriate, and clearly advise contacting emergency services if the user appears to be in danger.
"""

def build_messages(system_prompt: str, mood: str, user_text: str):
    """
    Returns a list of messages for OpenAI ChatCompletion API.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"MOOD: {mood}\nUser says: {user_text}\n\nInstructions for the assistant: respond as a calm, empathetic peer. "
            "Offer one short supportive reflection, one coping suggestion, and one resource/action the user can take next."
        },
    ]
    return messages
