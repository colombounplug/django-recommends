from django.contrib.contenttypes.models import ContentType
from .distances import sim_distance, sim_pearson


def topMatches(prefs, person, n=5, similarity=sim_pearson):
    """
    Returns the best matches for person from the prefs dictionary.
    Number of results and similarity function are optional params.
    """

    scores = [(similarity(prefs, person, other), other) for other in prefs if other != person]
    # Sort the list so the highest scores appear at the top
    scores.sort()
    scores.reverse()
    return scores[0:n]


def getRecommendations(prefs, person, similarity=sim_pearson):
    """
    Gets recommendations for a person by using a weighted average
    of every other user's rankings
    """

    totals = {}
    simSums = {}
    for other in prefs:
        # don't compare me to myself
        if other == person:
            continue
        sim = similarity(prefs, person, other)

        # ignore scores of zero or lower
        if sim <= 0:
            continue
        for item in prefs[other]:

            # only score movies I haven't seen yet
            if item not in prefs[person] or prefs[person][item] == 0:
                # Similarity * Score
                totals.setdefault(item, 0)
                totals[item] += prefs[other][item] * sim
                # Sum of similarities
                simSums.setdefault(item, 0)
                simSums[item] += sim
    # Create the normalized list
    rankings = [(total / simSums[item], item) for item, total in totals.items()]
    # Return the sorted list
    rankings.sort()
    rankings.reverse()
    return rankings


def transformPrefs(prefs):
    result = {}
    for person in prefs:
        for item in prefs[person]:
            result.setdefault(item, {})
            # Flip item and person
            result[item][person] = prefs[person][item]
    return result


def calculateSimilarItems(prefs, n=10):
    """
    Create a dictionary of items showing which other items they
    are most similar to.
    """

    result = {}
    # Invert the preference matrix to be item-centric
    itemPrefs = transformPrefs(prefs)
    c = 0
    for item in itemPrefs:
        # Status updates for large datasets
        c += 1
        if c % 100 == 0:
            print "%d / %d" % (c, len(itemPrefs))
        # Find the most similar items to this one
        scores = topMatches(itemPrefs, item, n=n, similarity=sim_distance)
        result[item] = scores
    return result


def getRecommendedItems(prefs, itemMatch, user):
    userRatings = prefs[user]
    scores = {}
    totalSim = {}

    # Loop over items rated by this user
    for (item, rating) in userRatings.items():

        # Loop over items similar to this one
        for (similarity, item2) in itemMatch[item]:
            # Ignore if this user has already rated this item
            if item2 in userRatings:
                continue

            # Weighted sum of rating times similarity
            scores.setdefault(item2, 0)
            scores[item2] += similarity * rating

            # Sum of all the similarities
            totalSim.setdefault(item2, 0)
            totalSim[item2] += similarity

    # Divide each total score by total weighting to get an average
    rankings = [(score / totalSim[item], item) for item, score in scores.items()]

    # Return the rankings from highest to lowest
    rankings.sort()
    rankings.reverse()
    return rankings


def convert_to_prefs(qs, func):
    """
    `func` must be a function that, given an item from qs, returns a tuple
    composed of (user_id, object_identifier, rating)

    `object_identifier` is any string that uniquely identifies the object ie:
    <app_label>.<model>:<object_id>.

    The `utils.get_identifier` method is provided as convenience for creatiing such identifiers.
    """
    prefs_tuple = map(func, qs)
    prefs = {}
    for pref in prefs_tuple:
        prefs[pref[0]][pref[1]] = pref[2]

    return prefs


def get_identifier(obj):
    """
    Given a Django Model, returns a string identifier in the format
    <app_label>.<model>:<object_id>.
    """
    ctype = ContentType.objects.get_for_model(obj)
    return "%s.%s:%s" % (ctype.app_label, ctype.model, obj.id)