# urlshortstd
Python standard library url shortener, made as a learning experience.
Written using Python 3.12.
Simply run with
`python -m src.app [PORT=8000]`

Make new shortened url with post request like curl example:
`curl -X POST http://localhost:8000/shorten -H "Content-Type: application/json" -d '{"url": "https://google.com"}'`

Run tests with
`python -m tests.test_e2e`

Note that this is not secure and should not be used.
