/**
 * Template Editor - Drag and Drop Placeholder Chips
 * Vanilla JS, no framework, no build step.
 * Scoped to template editor contentEditable fields only.
 */

(function() {
    'use strict';

    function initTemplateEditor() {
        const editors = document.querySelectorAll('.template-editor');
        
        editors.forEach(editor => {
            const templateId = editor.dataset.templateId;
            const subjectEditor = editor.querySelector('.editor-subject');
            const bodyEditor = editor.querySelector('.editor-body');
            const subjectHidden = editor.querySelector('input[name$="_subject"]');
            const bodyHidden = editor.querySelector('input[name$="_body"]');
            const chipsContainer = editor.querySelector('.placeholder-chips');
            
            if (!subjectEditor && !bodyEditor) return;

            // Make chips draggable
            const chips = chipsContainer?.querySelectorAll('.placeholder-chip');
            chips?.forEach(chip => {
                chip.addEventListener('dragstart', handleDragStart);
            });

            // Set up drop zones
            [subjectEditor, bodyEditor].forEach(editable => {
                if (!editable) return;
                
                editable.addEventListener('dragover', handleDragOver);
                editable.addEventListener('drop', handleDrop);
                editable.addEventListener('paste', handlePaste);
                
                // Sync content to hidden input on input
                editable.addEventListener('input', () => {
                    const hidden = editable === subjectEditor ? subjectHidden : bodyHidden;
                    if (hidden) {
                        hidden.value = editable.textContent || '';
                    }
                });
            });

            // Initial sync
            if (subjectHidden && subjectEditor) {
                subjectHidden.value = subjectEditor.textContent || '';
            }
            if (bodyHidden && bodyEditor) {
                bodyHidden.value = bodyEditor.textContent || '';
            }
        });
    }

    function handleDragStart(e) {
        const chip = e.target.closest('.placeholder-chip');
        if (!chip) return;
        
        e.dataTransfer.setData('text/plain', chip.dataset.column);
        e.dataTransfer.effectAllowed = 'copy';
        chip.classList.add('dragging');
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        
        const editor = e.target.closest('[contenteditable="true"]');
        if (editor) {
            editor.classList.add('drag-over');
        }
    }

    function handleDrop(e) {
        e.preventDefault();
        
        const editor = e.target.closest('[contenteditable="true"]');
        if (!editor) return;
        
        editor.classList.remove('drag-over');
        
        const columnName = e.dataTransfer.getData('text/plain');
        if (!columnName) return;
        
        const placeholderText = `{{${columnName}}}`;
        
        // Insert at cursor position
        insertAtCursor(editor, placeholderText);
        
        // Sync to hidden input
        const templateId = editor.closest('.template-editor').dataset.templateId;
        const hidden = editor.classList.contains('editor-subject') 
            ? document.querySelector(`input[name="template_${templateId}_subject"]`)
            : document.querySelector(`input[name="template_${templateId}_body"]`);
        
        if (hidden) {
            hidden.value = editor.textContent || '';
        }
    }

    function handlePaste(e) {
        // Strip HTML formatting on paste, keep only text
        e.preventDefault();
        const text = e.clipboardData.getData('text/plain');
        document.execCommand('insertText', false, text);
    }

    function insertAtCursor(editor, text) {
        const sel = window.getSelection();
        
        if (sel.rangeCount > 0) {
            const range = sel.getRangeAt(0);
            
            // Ensure we're inside the editor
            if (!editor.contains(range.startContainer) && !editor.contains(range.endContainer)) {
                // Click was outside, append to end
                editor.focus();
                const newRange = document.createRange();
                newRange.selectNodeContents(editor);
                newRange.collapse(false);
                sel.removeAllRanges();
                sel.addRange(newRange);
            }
            
            // Delete selected content
            range.deleteContents();
            
            // Insert text
            const textNode = document.createTextNode(text);
            range.insertNode(textNode);
            
            // Move cursor after inserted text
            range.setStartAfter(textNode);
            range.setEndAfter(textNode);
            sel.removeAllRanges();
            sel.addRange(range);
        } else {
            // No selection, append at end
            editor.focus();
            const range = document.createRange();
            range.selectNodeContents(editor);
            range.collapse(false);
            sel.removeAllRanges();
            sel.addRange(range);
            insertAtCursor(editor, text);
        }
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTemplateEditor);
    } else {
        initTemplateEditor();
    }

    // Also handle dynamic template additions (via HTMX)
    document.body.addEventListener('htmx:afterSwap', function(e) {
        if (e.detail.target.querySelector('.template-editor')) {
            initTemplateEditor();
        }
    });
})();