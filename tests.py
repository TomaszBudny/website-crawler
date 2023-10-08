# tests.py

from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from axe_selenium_python import Axe
import time

api_key =  "AIzaSyAMQcTal1y3MrRDriu9Efu2c31AOZDZjOs"

# List of violation descriptions to ignore
IGNORED_VIOLATIONS = [
    "Ensures all page content is contained by landmarks",
    "Ensures role attribute has an appropriate value for the element"
    # Add more violations to ignore as needed
]

def check_gtm_installed(url):
    """Check if Google Tag Manager is installed on the provided URL."""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Search for GTM script tags
    gtm_script_tags = soup.find_all('script', string=lambda x: 'GTM-' in x if x else False)

    return 'V' if gtm_script_tags else 'X'

def get_pagespeed_score(url):
    """Retrieve the Google PageSpeed Insights score for mobile."""
    API_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        'url': url,
        'category': ['performance', 'seo', 'best-practices'],
        'strategy': 'mobile',
        'key': api_key
    }
    
    response = requests.get(API_ENDPOINT, params=params)
    result = response.json()
    
    # Extract the scores for Performance, Best Practices, and SEO
    categories = result.get('lighthouseResult', {}).get('categories', {})
    
    performance_score = categories.get('performance', {}).get('score')
    best_practices_score = categories.get('best-practices', {}).get('score')
    seo_score = categories.get('seo', {}).get('score')
    
    if performance_score is not None:
        performance_score *= 100
    if best_practices_score is not None:
        best_practices_score *= 100
    if seo_score is not None:
        seo_score *= 100

    return (f"Scores for {url}:\n"
            f"Performance: {performance_score}\n"
            f"Best Practices: {best_practices_score}\n"
            f"SEO: {seo_score}")

def structured_headings(soup):
    """Parse and structure headings from the page into nested HTML lists."""
    headings = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    current_level = 0
    structured_list = []

    for tag in soup.find_all(headings):
        level = int(tag.name[1])

        # If current tag level is higher than current level, start a new list
        while level > current_level:
            structured_list.append('<ul>')
            current_level += 1

        # If current tag level is lower than current level, end the current list
        while level < current_level:
            structured_list.append('</ul>')
            current_level -= 1

        # Add the current heading to the list
        structured_list.append(f"<li>{tag.name}: {tag.text.strip()}</li>")

    # Close any remaining lists
    while current_level > 0:
        structured_list.append('</ul>')
        current_level -= 1

    return "\n".join(structured_list) if structured_list else None

def w3c_validation(url):
    # W3C validation API endpoint
    w3c_validator_url = "https://validator.w3.org/nu/"
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "text/html; charset=utf-8"
    }
    
    params = {
        "out": "json",
        "doc": url
    }
    
    response = requests.get(w3c_validator_url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if "messages" in data:
            errors = [msg for msg in data["messages"] if msg["type"] == "error"]
            
            if errors:
                print(f"Found {len(errors)} errors:")
                for error in errors:
                    print(f"- {error['message']} (Line: {error['lastLine']})")
            else:
                print("No errors found!")
        else:
            print("No messages from W3C validator.")
    else:
        print(f"Failed to check W3C validation. Status code: {response.status_code}")

def check_h1_tag(soup):
    """Retrieve the content of the h1 tag from the page."""
    h1_tag = soup.find('h1')
    return h1_tag.text.strip() if h1_tag else None

def check_title_tag(soup):
    """Retrieve the content of the title tag from the page."""
    title_tag = soup.find('title')
    return title_tag.text if title_tag else None

def check_meta_description(soup):
    """Retrieve the content of the meta description from the page."""
    meta_desc = soup.find('meta', attrs={"name": "description"})
    return meta_desc['content'] if meta_desc and 'content' in meta_desc.attrs else None

def check_meta_robots(soup):
    """Retrieve the content of the meta robots tag from the page."""
    meta_robots = soup.find('meta', attrs={"name": "robots"})
    return meta_robots['content'] if meta_robots and 'content' in meta_robots.attrs else None

def check_wordpress_version(soup):
    """Retrieve the WordPress version from the page, if available."""
    wp_version_tag = soup.find('meta', attrs={"name": "generator"})
    if wp_version_tag and 'content' in wp_version_tag.attrs:
        content = wp_version_tag['content']
        if "WordPress" in content:
            return content.replace("WordPress", "").strip()
    return None

def get_page_weight(content):
    """Get the weight (size in bytes) of the page."""
    return len(content)

def run_accessibility_check(url):
    # Each thread gets its own WebDriver instance
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    # options.add_argument("--silent")
    
    driver = webdriver.Chrome(options=options)
    axe = Axe(driver)

    driver.get(url)

    # If it's the starting URL, add the "contrast" cookie and refresh the page
    # driver.add_cookie({"name": "contrast", "value": "true"})

    # time.sleep(1)  # Wait for a second to allow potential changes to take effect
    axe.inject()
    audit_result = axe.run()

    # results = {}
    violations_to_report = [v for v in audit_result["violations"] if v['description'] not in IGNORED_VIOLATIONS]
    # if violations_to_report:
    #     results[url] = [violation['description'] for violation in violations_to_report]
    # print(f"{url} : {results[url]}")

    print(f"{url} : {[violation['description'] for violation in violations_to_report]}")

    driver.quit()

    formatted_output = "\n".join(violation['description'] for violation in violations_to_report)
    
    return formatted_output
