import click
import sys
import asyncio
import textwrap
import random
import os

from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.completion import NestedCompleter

from datetime import datetime
from tabulate import tabulate
from tqdm import tqdm
from bs4 import BeautifulSoup
from pyppeteer import launch

async def get_browser(headless, auto_close):
    return await launch(
        headless=headless,
        autoClose=auto_close
    )

class Task:
    def __init__(self, subject, status, summary, url, issued, due, for_class, issuer, attachments, description):
        self.subject = subject
        self.status = status
        self.summary = summary
        self.url = url
        self.for_class = for_class
        self.issuer = issuer
        self.attachments = attachments
        self.description = description
        
        self.issued = datetime.strptime(issued, "%d/%m/%Y")
        self.due = datetime.strptime(due, "%d/%m/%Y")

    def hash(self):
        random.seed(self.subject + self.summary + self.url + self.description)

        with open(os.path.join(os.path.dirname(__file__), "adjectives.txt"), "r") as f:
            adjectives = f.readlines()
            
        with open(os.path.join(os.path.dirname(__file__), "nouns.txt"), "r") as f:
            nouns = f.readlines()

        return random.choice(adjectives).strip('\n')+"-"+random.choice(nouns).strip('\n')


    def as_list(self, short=True):
        if short:
            return [
                self.hash(),
                self.subject,
                "\n".join(textwrap.wrap(self.summary, width=50)),
                self.due.strftime("%Y-%m-%d"),
            ]
        else:

            summary = "\n".join(textwrap.wrap(self.summary, width=40))
            description = "\n".join(textwrap.wrap(self.description, width=40))
            attachments = "\n".join(self.attachments)

            return [
                self.hash(),
                self.subject,
                summary,
                description,
                attachments,
                self.issuer,
                self.issued.strftime("%Y-%m-%d"),
                self.due.strftime("%Y-%m-%d"),
            ]


def task_table(tasks, short=True):
    tasks = [task.as_list(short) for task in tasks]

    if short:
        print(
            tabulate(tasks, headers=["Name", "Subject", "Summary", "Due"], tablefmt="fancy_grid")
        )

    else:
        print(
            tabulate(tasks, headers=["Name", "Subject", "Summary", "Description", "Attachments", "Issuer", "Issed", "Due"], tablefmt="fancy_grid")
        )

async def get_tasks():
    browser = await get_browser(False, True)
    page = (await browser.pages())[0]

    click.echo("Logging in...")
    await page.goto("https://insight.burgate.hants.sch.uk/secure.aspx?ReturnUrl=%2fInfo.aspx")
    await page.click("#UserName")
    await page.keyboard.type("")

    await page.click("#Password")
    await page.keyboard.type("")

    await page.click("#Login1_login")

    click.echo("Waiting for info page...")
    await page.waitForSelector("#newAssignments")
    await page.click("#newAssignments")

    click.echo("Waiting for assignments page...")
    await page.waitForSelector(".assignmentstable")

    html = await page.evaluate("(html) => document.querySelector('.assignmentstable').outerHTML")
    soup = BeautifulSoup(html, "lxml")
    table = soup.find_all('table')[0]

    await browser.close()

    tasks = []
    
    for i, row in tqdm(enumerate(table.find_all('tr')), desc="Parsing assigments table"):
        # There's two types of rows in the response:
        # <tr data-id="..." data-sb="..."></tr> -- A task "header"
        # <tr data-sn="1"></tr> -- A task description
        #
        # The columns are layed out like so:
        # Subject   Status  Summary URL Issued  Due Class   Issuer  Attachments

        # For task headers:
        if row.has_attr("data-id"):
            columns = row.find_all('td')
            attachments = [x.get('href') for x in columns[8].find_all('a')]

            tasks.append(
                Task(
                    columns[0].text,
                    columns[1].text,
                    columns[2].text,
                    columns[3].text,
                    columns[4].text,
                    columns[5].text,
                    columns[6].text,
                    columns[7].text,
                    attachments,
                    "",
                )
            )

        # For task descriptions:
        if row.get("data-sn") == "1":
            tasks[-1].description = row.text

    return tasks

def main(args):
    """ins is a command-line client for Insight"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = loop.run_until_complete(get_tasks())

    task_table(tasks)
    task_names_complete = {task.hash():None for task in tasks}

    completer = NestedCompleter.from_nested_dict({  
        "ls": None,
        "ls -a": None,
        "info": task_names_complete,
        "exit": None,
    } )

    text = PromptSession(completer=completer)

    while True:
        action = text.prompt("action> ")
        arguments = action.split(" ")[1:]

        if action == "exit":
            return

        elif action == "ls":
            task_table(tasks)

        elif action.startswith("info"):
            if len(arguments) != 1:
                print("usage: info <name>")
                continue

            task_table([task for task in tasks if task.hash() == arguments[0]], False)

        elif action == "ls -a":
            task_table(tasks, short=False)
    

@click.command()
def run():
    """
    Entry point for command-line applications.
    """
    main(sys.argv[1:])

