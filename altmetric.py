import json
import urllib.request
import time
import os
import pymysql.cursors
import pymysql.err

def connect_mysql_server(username, db_password, db_hostname, database_name):
    """Establish a connection to MySQL or MariaDB server. This function is
    depandend on the PyMySQL library.
    See: https://github.com/PyMySQL/PyMySQL

    Args:
        username (string): username of the database user.
        password (string): password of the database user.
        db_hostname (string): hostname or IP address of the database server.
        database_name (string): the name of the database we are connecting to.

    Returns:
        MySQLConnection object.
    """
    return pymysql.connect(user=username,
                           password=db_password,
                           host=db_hostname,
                           database=database_name)

def truncate_altmetric(mysql_cursor):
    """This function will delete all rows in the altmetric table when called.

    Args:
        mysql_cursor (CMySQLCursor): Executes an SQL query against the database.
    """
    trucate_altmetric_query = (
        """
        truncate altmetric;
        """
    )

    mysql_cursor.execute(trucate_altmetric_query)

def get_altmetric_doi(mysql_cursor):
    """Gets the doi column from the altmetric table

    Args:
        mysql_cursor (CMySQLCursor): Executes an SQL query against the database.

    Returns:
        doi (list): List of all rows in the doi column.
    """
    get_metadata_query = (
        """
        SELECT doi FROM reciter.altmetric
        """
    )

    mysql_cursor.execute(get_metadata_query)

    doi = list()

    for record in mysql_cursor:
        doi.append(record[0])

    return doi

def get_personArticle_doi(mysql_cursor):
    """Gets the doi column from the personArticle table

    Args:
        mysql_cursor (CMySQLCursor): Executes an SQL query against the database.

    Returns:
        (list): List of all rows in the doi column.
    """
    get_metadata_query = (
        """
        select distinct
            doi,
            pmid,
            datePublicationAddedToEntrez
        from reciter.personArticle
            where userAssertion = 'ACCEPTED'
                and round((UNIX_TIMESTAMP() - UNIX_TIMESTAMP(
                                                STR_TO_DATE(datePublicationAddedToEntrez,
                                                    '%Y-%m-%d'))) / (60*60*24),0)  < 730
        """
    )

    mysql_cursor.execute(get_metadata_query)

    doi = list()

    for record in mysql_cursor:
        doi.append(record[0])

    return doi

def list_diff(list1, list2):
    """Finds the values in list1 that do not
        exist in list2.

    Args:
        list1 (list): List we check against.
        list2 (list): List with values that are duplicate in list1.

    Returns:
        list: Contains unique values.
    """
    return list(set(list1) - set(list2))

def list_to_lowercase(list_with_uppercase):
    """Changes every capital letter in the list with lowercase.

    Args:
        list_with_uppercase (list): List that contains capitalized letters and words.
    """
    map(str.lower, list_with_uppercase)

def create_article_url(article_doi):
    """Create altmetric API URL by combining the base API and doi.

    Args:
        article_doi (string): API doi field.

    Returns:
        string: Full API URL of the record.
    """
    API_BASE_URL = "https://api.altmetric.com/v1/doi/"

    api_url = list()

    for doi in article_doi:
        if doi != "":
            api_url.append(API_BASE_URL + doi)

    return api_url

def get_json_data(api_record_url):
    """Gets JSON data from API URL

    Args:
        api_record_url (string): URL of the API returning JSON data.

    Returns:
        dict: Python dictionary with JSON data or error.
    """
    try:
        api_request = urllib.request.urlopen(api_record_url)
        json_api_data = json.loads(api_request.read().decode())
        return json_api_data
    except urllib.error.URLError as err:
        print("%s for API record URL: %s" % (err, api_record_url))
    except ValueError as err:
        print("Problem parsing JSON data. Error %s" % (err))


def get_dict_value(dict_obj, *keys):
    """Gets the value of a key in a dictionary object.
        If the key is not found it returns None.

    Args:
        dict_obj (dict): Dictionary object to check.
        keys (string): Name of key or nested keys to search.

    Raises:
        AttributeError: If dictionary object is not passwed.

    Returns:
        Value of the key if found or None if not.
    """
    if not isinstance(dict_obj, dict):
        raise AttributeError("dict_obj needs to be of type dict.")

    dict_value = dict_obj

    for key in keys:
        try:
            dict_value = dict_value[key]
        except KeyError:
            return None
    return dict_value


def insert_altmetric_record(api_url, mysql_db, mysql_cursor):
    """Inserts the API record in the MySQL database table.

    Args:
        api_url (string): URL of the API record.
        mysql_db (MySQLConnection object): The MySQL database where the table resides.
        mysql_cursor (CMySQLCursor): Executes an SQL query against the database.

    Returns:
        string: Record added successfully or error message.
    """
    altmetric_record = get_json_data(api_url)

    if isinstance(altmetric_record, dict):
        # We map dictionary value to each database table. This should
        # allow for easy update if the database tables or API records
        # change in the future. In that case, we should only need to
        # update this function.
        #
        # Because the API does not always return data for all keys,
        # we have to check each one and assign None (NULL) for the
        # missing values.

        add_to_altmetric_table = (
            """
            INSERT INTO reciter.altmetric(
                `doi`,
                `pmid`,
                `altmetric_jid`,
                `context-all-count`,
                `context-all-mean`,
                `context-all-rank`,
                `context-all-pct`,
                `context-all-higher_than`,
                `context-similar_age_3m-count`,
                `context-similar_age_3m-mean`,
                `context-similar_age_3m-rank`,
                `context-similar_age_3m-pct`,
                `context-similar_age_3m-higher_than`,
                `altmetric_id`,
                `cited_by_msm_count`,
                `cited_by_posts_count`,
                `cited_by_tweeters_count`,
                `cited_by_feeds_count`,
                `cited_by_fbwalls_count`,
                `cited_by_rh_count`,
                `cited_by_accounts_count`,
                `last_updated`,
                `score`,
                `history-1y`,
                `history-6m`,
                `history-3m`,
                `history-1m`,
                `history-1w`,
                `history-at`,
                `added_on`,
                `published_on`,
                `readers-mendeley`
            )
            VALUES(
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s
            )
            """
        )

        try:
            doi = get_dict_value(altmetric_record, "doi")
            pmid = get_dict_value(altmetric_record, "pmid")
            altmetric_jid = get_dict_value(altmetric_record, "altmetric_jid")
            context_all_count = get_dict_value(altmetric_record, "context", "all", "count")
            context_all_mean = get_dict_value(altmetric_record, "context", "all", "mean")
            context_all_rank = get_dict_value(altmetric_record, "context", "all", "rank")
            context_all_pct = get_dict_value(altmetric_record, "context", "all", "pct")
            context_all_higher_than = get_dict_value(altmetric_record,
                                                    "context",
                                                    "all",
                                                    "higher_than")
            context_similar_age_3m_count = get_dict_value(altmetric_record,
                                                        "context",
                                                        "similar_age_3m",
                                                        "count")
            context_similar_age_3m_mean = get_dict_value(altmetric_record,
                                                        "context",
                                                        "similar_age_3m",
                                                        "mean")
            context_similar_age_3m_mean = get_dict_value(altmetric_record,
                                                        "context",
                                                        "similar_age_3m",
                                                        "mean")
            context_similar_age_3m_rank = get_dict_value(altmetric_record,
                                                        "context",
                                                        "similar_age_3m",
                                                        "rank")
            context_similar_age_3m_pct = get_dict_value(altmetric_record,
                                                        "context",
                                                        "similar_age_3m",
                                                        "pct")
            context_similar_age_3m_higher_than = get_dict_value(altmetric_record,
                                                                "context",
                                                                "similar_age_3m",
                                                                "higher_than")
            altmetric_id = get_dict_value(altmetric_record, "altmetric_id")
            cited_by_msm_count = get_dict_value(altmetric_record, "cited_by_msm_count")
            cited_by_posts_count = get_dict_value(altmetric_record, "cited_by_posts_count")
            cited_by_tweeters_count = get_dict_value(altmetric_record, "cited_by_tweeters_count")
            cited_by_feeds_count = get_dict_value(altmetric_record, "cited_by_feeds_count")
            cited_by_fbwalls_count = get_dict_value(altmetric_record, "cited_by_fbwalls_count")
            cited_by_rh_count = get_dict_value(altmetric_record, "cited_by_rh_count")
            cited_by_accounts_count = get_dict_value(altmetric_record, "cited_by_accounts_count")
            last_updated = get_dict_value(altmetric_record, "last_updated")
            score = get_dict_value(altmetric_record, "score")
            history_1y = get_dict_value(altmetric_record, "history", "1y")
            history_6m = get_dict_value(altmetric_record, "history", "6m")
            history_3m = get_dict_value(altmetric_record, "history", "3m")
            history_1m = get_dict_value(altmetric_record, "history", "1m")
            history_1w = get_dict_value(altmetric_record, "history", "1w")
            history_at = get_dict_value(altmetric_record, "history", "at")
            added_on = get_dict_value(altmetric_record, "added_on")
            published_on = get_dict_value(altmetric_record, "published_on")
            readers_mendeley = get_dict_value(altmetric_record, "readers", "mendeley")

            new_record = (doi,
                          pmid,
                          altmetric_jid,
                          context_all_count,
                          context_all_mean,
                          context_all_rank,
                          context_all_pct,
                          context_all_higher_than,
                          context_similar_age_3m_count,
                          context_similar_age_3m_mean,
                          context_similar_age_3m_rank,
                          context_similar_age_3m_pct,
                          context_similar_age_3m_higher_than,
                          altmetric_id,
                          cited_by_msm_count,
                          cited_by_posts_count,
                          cited_by_tweeters_count,
                          cited_by_feeds_count,
                          cited_by_fbwalls_count,
                          cited_by_rh_count,
                          cited_by_accounts_count,
                          last_updated,
                          score,
                          history_1y,
                          history_6m,
                          history_3m,
                          history_1m,
                          history_1w,
                          history_at,
                          added_on,
                          published_on,
                          readers_mendeley)

            mysql_cursor.execute(add_to_altmetric_table, new_record)
            mysql_db.commit()

            print("Record %s added to the database." % (api_url))

        except pymysql.err.MySQLError as err:
            print("Error writing the record to the database. %s" % (err))

    else:
        print("Invalid record obtained from API URL")

if __name__ == '__main__':
    DB_USERNAME = os.getenv('DB_USERNAME')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_NAME = os.getenv('DB_NAME')

    # Create a connection to get metadata from the
    # personArticle table. This data is used to
    # generate the API URL.
    person_article_db = connect_mysql_server(DB_USERNAME, DB_PASSWORD, DB_HOST, DB_NAME)
    person_article_cursor = person_article_db.cursor()

    # Create a connection to use for inserting a record
    # to the altmetric table. This is the API response
    # we need to populate the altmetric table.
    altmetric_db = connect_mysql_server(DB_USERNAME, DB_PASSWORD, DB_HOST, DB_NAME)
    altmetric_cursor = altmetric_db.cursor()
    person_article_doi = get_personArticle_doi(person_article_cursor)
    altmetric_doi = get_altmetric_doi(altmetric_cursor)

    # Truncate the altmetric table
    truncate_altmetric(altmetric_cursor)

    # Convert the DOI to lowercase. In some entries the DOI
    # capitalized and that causes problems with comparing the list.
    # the API returns lowecase, so they should be lower.
    #
    # During testing it looks like this is useful even when altmetric
    # is empty because there is duplicate data in our personArticle table,
    # so this step drops the dubpicate records from the URL list.
    url_doi = list_diff(map(str.lower, person_article_doi), map(str.lower, altmetric_doi))

    article_api_url = create_article_url(url_doi)

    for url in article_api_url:
        insert_altmetric_record(url, altmetric_db, altmetric_cursor)
        time.sleep(1)

    person_article_db.close()
    person_article_cursor.close()
    altmetric_db.close()
    altmetric_cursor.close()
