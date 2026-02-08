# Contributing to Kalshi Markets Dashboard

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in credentials
5. Initialize database:
   ```bash
   python bootstrap.py
   ```

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and under 50 lines when possible

## Testing

Before submitting a PR:

1. Test data ingestion:
   ```bash
   python workers/ingest.py
   ```

2. Test email digest:
   ```bash
   python workers/emailer.py --force
   ```

3. Test Streamlit app:
   ```bash
   streamlit run app/main.py
   ```

4. Verify all pages load without errors

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Update README.md if needed
4. Test your changes thoroughly
5. Submit PR with clear description
6. Wait for review

## Reporting Issues

When reporting issues, include:
- Python version
- OS version
- Error messages and stack traces
- Steps to reproduce
- Expected vs actual behavior

## Feature Requests

Open an issue with:
- Clear description of the feature
- Use case and benefits
- Any implementation ideas

## Questions?

- Open a discussion on GitHub
- Check existing issues first

Thank you for contributing!
