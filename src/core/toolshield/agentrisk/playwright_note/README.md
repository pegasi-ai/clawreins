# Full Playwright Setup

After hosting the 3 websites (Reddit, Shopping, Shopping Admin), follow these steps:

## 1. Replace Prompt Files

Replace the content in the following files:

| Original File | Replace With |
|---------------|--------------|
| `toolshield/prompts.py` | `agentrisk/playwright_note/prompts_full_playwright.py` |
| `toolshield/post_process_prompts.py` | `agentrisk/playwright_note/post_process_prompts_full_playwright.py` |

## 2. Update Web Addresses

Run the following command to correct web page addresses in the code:
```bash
python agentrisk/playwright_note/correct_web_address.py --domain_name <YOUR_DOMAIN> --suffix <YOUR_SUFFIX>
```
