from typing import Union
import time
from datetime import datetime, timedelta, date
import psutil
import os
import threading
import snowflake_utils as sf
from dataclasses import dataclass
import argparse

recordset_size = 50000
month_increment = timedelta(days=31)
start_time = datetime.now()


def format_timedelta(td):
    # i hate fractional seconds
    td = str(td)
    return td[0: td.find(".")]


def report_resources(stop):
    gig = 1073741824
    # mb = 1048576
    while True:
        process = psutil.Process(os.getpid())
        used = process.memory_info().rss / gig
        avail = psutil.virtual_memory().available / gig

        # print(f"\nResources {datetime.now().isoformat()}")
        elapsed = datetime.now() - start_time

        print(f"Memory used: {round(used, 3)} G, avail: {round(avail, 3)} G, Elapsed {format_timedelta(elapsed)}")

        # print(f"CPU: {psutil.cpu_percent()}% {psutil.cpu_percent(percpu=True)}")
        time.sleep(7)
        if stop():
            print("Exiting reporting.")
            break


def reporting_decorator(func):
    def wrapped_func(*args):
        stop_reporting = False
        thread = threading.Thread(target=report_resources, args=(lambda: stop_reporting,))
        thread.start()
        func(*args)
        stop_reporting = True
        thread.join()

    return wrapped_func


def set_day_one(somedate: Union[datetime, date]) -> date:
    if type(somedate) == datetime:
        somedate = somedate.date()
    return somedate.replace(day=1)


def format_key(somedate: Union[datetime, date]) -> str:
    return somedate.strftime("%Y-%m")


@dataclass(frozen=True)
class Post:
    job_id: int
    post_date_ts: datetime
    remove_date_ts: datetime
    mapped_role: str
    salary: int
    region_state: str
    year_month: str
    days_active: int

    def get_start_month(self):
        return set_day_one(self.post_date_ts)

    def get_end_month(self):
        return set_day_one(self.remove_date_ts + month_increment)

    def get_formatted_key(self):
        return format_key(self.get_start_month())


@dataclass(frozen=True)
class PostMsa(Post):
    msa: str


class PostCounts:

    def __init__(self):
        self.dates = {}

    def __len__(self):
        return len(self.dates)

    def months(self):
        return self.dates.keys()

    def mapped_roles(self, month_key: str):
        if month_key not in self.dates:
            return []

        return list(self.dates[month_key].keys())

    def posts(self, month_key: str, mapped_role: str):
        if month_key not in self.dates or mapped_role not in self.dates[month_key]:
            return []
        return self.dates[month_key][mapped_role]

    def count_roles(self):
        for month, mapped_roles in self.dates.items():
            print(month, len(mapped_roles))

    def add(self, post, use_msa=False):

        # now add the month keys between the post date and remove date
        cur_month = post.get_start_month()

        while cur_month < post.get_end_month():
            month_key = format_key(cur_month)
            if month_key not in self.dates:
                self.dates[month_key] = {}

            if use_msa:
                mapped_role = (post.mapped_role, post.msa.replace("'", "''"))
            else:
                mapped_role = post.mapped_role

            if post.mapped_role not in self.dates[month_key]:
                self.dates[month_key][mapped_role] = set()

            self.dates[month_key][mapped_role].add(post)

            cur_month = set_day_one(cur_month + month_increment)


class PostAggregate:

    def __init__(self, month_key, mapped_role, posts: set[Post], use_msa=None):

        self.month_key = month_key
        self.mapped_role = mapped_role
        self.use_msa = use_msa
        self.new_posts = 0

        # compute stats for month/year
        salary_sum = 0
        days_active_sum = 0
        no_salary_posts = 0

        for post in posts:

            if post.get_formatted_key() == month_key:
                self.new_posts += 1

            if post.salary:
                salary_sum += post.salary
            else:
                no_salary_posts += 1

            days_active_sum += post.days_active

        self.avg_days_active = days_active_sum / len(posts)

        salary_posts = len(posts) - no_salary_posts
        if salary_posts:
            self.avg_salary = salary_sum / salary_posts
        else:
            self.avg_salary = "NULL"

        self.active_posts = len(posts)

    def get_row(self):
        # this is used for the insert in to the postings_tthire table
        # so order needs to match get_columns()! could do this better

        # month_key, year, mapped_role, new_posts, active_posts, avg_salary, avg_days_active

        if self.use_msa:
            mapped_role, msa = self.mapped_role
            granularity = f"'{mapped_role}', '{msa}'"
        else:
            granularity = f"'{self.mapped_role}'"

        return f"('{self.month_key}', {self.month_key[0:4]}, {granularity}, {self.new_posts}, " \
               f"{self.active_posts}, {self.avg_salary}, {self.avg_days_active})"

    def get_columns(self):
        if self.use_msa:
            return "(year_month, post_year, mapped_role, msa, new_posts, active_posts, avg_salary, avg_days_post_active)"

        return "(year_month, post_year, mapped_role, new_posts, active_posts, avg_salary, avg_days_post_active)"


def count(sf_conn, use_msa=False, limit=""):
    # quoted field names are for getting back lowercase key names in the dictcursor row
    # who knew? This allows them to map directly to the Post object.

    if use_msa:
        msa = 'region_state as "msa",'

    if limit:
        limit = f"limit {limit}"  # that's fun

    # TODO you gotta figure out how to run this query in chunks so you're not still loading
    # nearly all of the dataset into memory.. like do a year a time or something

    tth_query = f"""   
    SELECT job_id as "job_id", 
    post_date::timestamp_ntz as "post_date_ts", 
    remove_date::timestamp_ntz as "remove_date_ts", 
    mr as "mr", 
    salary as "salary", 
    region_state as "region_state", 
    concat(year("post_date_ts"),'-', lpad(month("post_date_ts"), 2, '0')) as "year_month",
    {msa}
    datediff('day', "post_date_ts", "remove_date_ts") as "days_active"

    FROM postings
    WHERE mr IS NOT NULL
    and post_date is not null
    and remove_date is not null
    and year("post_date_ts") between 2016 and 2023
    order by "post_date_ts", "mapped_role", "region_state"

    {limit}
    
    """

    curs = sf.get_cursor(tth_query, conn=sf_conn)
    start = datetime.now()
    res = curs.fetchmany(recordset_size)

    post_counts = PostCounts()
    post_count = 0

    while res:

        for r in res:
            post_count += 1
            if use_msa:
                post = PostMsa(**r)
            else:
                post = Post(**r)

            post_counts.add(post, use_msa)

        print("Start months:", len(post_counts), "posts:", post_count, format_timedelta(datetime.now() - start))

        res = curs.fetchmany(recordset_size)

    return post_counts


@reporting_decorator
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-limit", help="limit for testing", required=False, type=int)
    parser.add_argument("--msa", help="group by msa", action="store_true")
    global recordset_size
    parser.add_argument("-rc", help="size of fetch", type=int, required=False, default=recordset_size)
    args = parser.parse_args()

    recordset_size = args.rc

    sf_conn = sf.get_connection()
    post_counts = count(sf_conn, args.msa, args.limit or "")

    insert_block_size = 1000
    rows = []

    table = "postings_1"
    if args.msa:
        table = "postings_2"

    def do_insert(post_agg):
        if not rows:
            return

        sql = f"Insert into {table} {post_agg.get_columns()} values"
        sql += ',\n'.join(rows)
        rc = sf_conn.cursor().execute(sql)
        print(f"Inserted {rc.rowcount} rows")

    pagg = None
    for month in post_counts.months():
        print(f"Aggregating {month}")

        for mapped_role in post_counts.mapped_roles(month):
            posts = post_counts.posts(month, mapped_role)
            pagg = PostAggregate(month, mapped_role, posts, use_msa=args.msa)
            rows.append(pagg.get_row())

            if len(rows) >= 10000:
                do_insert(pagg)
                rows = []

    # last insert of the remaining rows
    do_insert(pagg)


if __name__ == "__main__":
    main()
