def rank_locations(locations):
    """
    Rank candidate locations by final decision score.
    """

    return sorted(
        locations,
        key=lambda x: x["final_score"],
        reverse=True
    )
