"""AI prompt formatting utilities for Gemini API calls."""

from typing import List


def build_gemini_prompt(prompt_text: str, output_placeholders: List[str]) -> str:
    """
    Build the final prompt text to send to Gemini.
    
    Takes the user's prompt text (after CSV/manual substitutions) and appends
    formatting instructions telling Gemini to wrap each expected output value
    in an XML-style tag matching the placeholder name.
    
    Args:
        prompt_text: The user's prompt text after CSV/manual substitutions
        output_placeholders: List of expected output placeholder names
        
    Returns:
        The final prompt text ready to send to Gemini
    """
    if not output_placeholders:
        return prompt_text
    
    # Build the formatting instruction block
    instruction_lines = [
        "",
        "=== FORMATTING INSTRUCTIONS ===",
        "Return only the following, with no other text, no markdown, no explanation:",
        ""
    ]
    
    for placeholder in output_placeholders:
        instruction_lines.append(f"<{placeholder}>")
        instruction_lines.append("[value]")
        instruction_lines.append(f"</{placeholder}>")
        instruction_lines.append("")
    
    # Remove the last empty line
    if instruction_lines and instruction_lines[-1] == "":
        instruction_lines.pop()
    
    formatting_block = "\n".join(instruction_lines)
    
    # Combine user prompt with formatting instructions
    return prompt_text.rstrip() + "\n\n" + formatting_block