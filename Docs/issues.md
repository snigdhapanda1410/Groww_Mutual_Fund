# Issue Log & Resolution

## Issue: Inline Markdown Links Embedded in Response Body
**Description**: The response body included raw inline markdown links such as `[GrowwPage](https://groww.in/mutual-funds/...)`, which duplicated the UI's dedicated citation badge and cluttered the factual text.

### Example Before Fix:
```markdown
Investor Query: Who is the fund manager for HDFC Large and Mid Cap Fund
Groww Facts Engine • Grounded Verification
The fund manager for the HDFC Large and Mid Cap Fund (Direct – Growth) is Prashant Jain. [GrowwPage](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth)
🔗 Groww Scheme Page ↗
Last updated from sources: 2026-10-23
```

### Resolution Applied:
1. **System Prompt Update** (`src/generation/prompt_templates.py`):
   - Updated Rule 5 to explicitly instruct the model: `NO INLINE LINKS: Provide only clean factual text sentences. Do NOT include inline markdown links, citation brackets, or URLs (such as [GrowwPage](...) or raw URLs) in your sentences.`
2. **Output Contract Validator** (`src/generation/output_formatter.py`):
   - Enhanced `extract_content_body` with regex to automatically strip any inline markdown links (`[Text](URL)`), raw URLs, or full-width citation brackets (`【...】`) from the content sentences.
   - Enforced that the canonical citation `**Source**: [Groww Scheme Page]({clean_url})` is strictly positioned in its own block outside the factual sentences.
3. **UI Component Sanitization** (`ui/components.py`):
   - Added regex sanitization in `render_assistant_message` to strip any stray markdown links from the card body before HTML rendering, ensuring only the dedicated `🔗 Groww Scheme Page ↗` citation badge displays.

### Verified Result After Fix:
```markdown
Investor Query: Who is the fund manager for HDFC Large and Mid Cap Fund
Groww Facts Engine • Grounded Verification
The fund manager for the HDFC Large and Mid Cap Fund (Direct – Growth) is Prashant Jain.
🔗 Groww Scheme Page ↗
Last updated from sources: 2026-10-23
```
*Status: Resolved and verified across all 207 automated tests.*