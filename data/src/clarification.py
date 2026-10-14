def needs_clarification(query):

    if not query or len(query.split()) < 2:
        return True

    return False


def generate_clarification(query):

    return "Could you please provide more details about your question?"
