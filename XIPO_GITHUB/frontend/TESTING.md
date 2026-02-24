# Testing Streamlit UI Patches

## Changes Made

1. **Fixed API Call**:
   - Now strips whitespace from company name before sending
   - Sends exactly: `{"company_name": company_name.strip(), "top_k": 6, "debug": false}`

2. **Improved Error Handling**:
   - Displays status code clearly
   - Shows raw response text for debugging
   - Properly parses JSON for 404 responses
   - Clears old results when searching for new company

3. **Added Debug Expander**:
   - Shows backend response details
   - Displays status code and URL
   - Shows full JSON response or raw text
   - Available for both success and error cases

4. **Better State Management**:
   - Stores `debug_response` in session state
   - Clears old results when new company is searched
   - Prevents displaying stale data

## How to Test

### Test 1: Company Found on Later Pages

Try a company that requires pagination to find (not in first 25 results):

```
Company: "Brigade Hotel"
```

**Expected behavior:**
- Should find "Brigade Hotel Ventures Limited- RHP"
- Health score and report should display
- Debug expander shows status 200
- Can ask questions in chatbot

### Test 2: Company Not Found (404)

Try a non-existent or very old company:

```
Company: "XYZ Nonexistent Company"
```

**Expected behavior:**
- Error message: "No strong match found"
- Shows "Did you mean one of these?" with suggestions
- Debug expander shows status 404
- Shows top_matches from SEBI scraper
- Old results are cleared

### Test 3: Company with Exact Match

Try a recent IPO company:

```
Company: "Meesho"
```

**Expected behavior:**
- Quick match (found on page 0)
- Score should be high (0.9+)
- Full report displays
- Debug expander shows complete JSON response

### Test 4: Backend Error (500)

To test error handling, you can temporarily break the backend or test with backend down:

**Expected behavior:**
- Shows error with status code
- Displays raw error message
- Debug expander shows error details

## Verification Checklist

- [ ] Company name is stripped before API call
- [ ] Debug expander appears after analysis
- [ ] Status code is displayed in debug
- [ ] JSON response is shown in debug (if available)
- [ ] Raw text is shown in debug (if JSON parse fails)
- [ ] Old results cleared when searching new company
- [ ] 404 responses show top_matches suggestions
- [ ] Error messages show status code and response text

## Running the Test

1. Ensure backend is running:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. Streamlit should auto-reload with changes:
   - If not, refresh the browser page
   - Or restart: `streamlit run app.py`

3. Test each scenario above and verify behavior
