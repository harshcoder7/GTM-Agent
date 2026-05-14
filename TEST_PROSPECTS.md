# Test prospects

| # | Path | Prospect | Why |
|---|---|---|---|
| 1 | Happy | Name: "Aravind Srinivas", Company: "Perplexity AI", Title: "CEO", LinkedIn: https://www.linkedin.com/in/aravsrinivas/ | Strong ICP fit for QpiAI (AI infra), high signal LinkedIn |
| 2 | Cold | Name: "Jane Smith", Company: "Local Bakery LLC", Title: "Owner" | ICP cold — bakery has no ML/agent use case; pipeline should refuse to draft |
| 3 | Placeholder leak | Same as #1 with `force_placeholder=true` | Gate 1 safety check must catch the leaked `{{first_name}}` |
| 4 | Low LinkedIn activity | Name: "John Doe", Company: "Acme Stealth Co", LinkedIn: a profile with <3 posts | Person Signal gracefully degrades; drafting falls back to company-level hook |
