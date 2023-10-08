# Web Crawler

This web crawler is designed to crawl websites and extract essential information while also performing comprehensive accessibility and performance checks on each page. The primary features include extracting titles, meta descriptions, H1 tags, page weights, and more. Additionally, the crawler uses the **axe accessibility engine** to inspect each page for accessibility issues, ensuring that web content is accessible to individuals with disabilities. This proactive testing can help identify potential violations of the Americans with Disabilities Act (ADA), thereby preventing possible discrimination claims. Moreover, the crawler checks each page using **Google PageSpeed Insights** to evaluate its performance, best practices, and SEO metrics, assisting in optimizing the website for better search engine rankings and conversions.

The application provides a user-friendly graphical interface powered by PyQt5, enabling users to input URLs and view the real-time crawled results seamlessly.

## Features

- Concurrent crawling using multiple threads.
- Real-time display of crawled results.
- **Accessibility Testing:** Evaluates each page using the axe accessibility engine, identifying potential ADA violations.
- **Performance and SEO Checks:** Analyzes each page with Google PageSpeed Insights to assess performance, best practices, and SEO metrics.
- Export results to a CSV file.
