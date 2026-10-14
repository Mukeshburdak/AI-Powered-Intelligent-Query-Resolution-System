def understand_query(query):

    query = query.strip()

    if not query:
        return {
            "valid": False,
            "query": ""
        }

    return {
        "valid": True,
        "query": query,
        "intent": "information_request"
    }
