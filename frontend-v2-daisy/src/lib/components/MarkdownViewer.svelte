<script lang="ts">
    import { marked } from 'marked';
    import DOMPurify from 'isomorphic-dompurify';

    let { content = "", preview = false, previewLength = 220 } = $props<{
        content: string;
        preview?: boolean;
        previewLength?: number;
    }>();

    // Full HTML — sanitized
    let html = $derived(DOMPurify.sanitize(marked.parse(content) as string));

    // Preview: strip all HTML tags, then truncate plain text
    let previewText = $derived.by(() => {
        const stripped = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
        if (stripped.length <= previewLength) return stripped;
        // Try to truncate at a word boundary
        const truncated = stripped.slice(0, previewLength);
        const lastSpace = truncated.lastIndexOf(' ');
        return (lastSpace > 0 ? truncated.slice(0, lastSpace) : truncated) + '…';
    });
</script>

{#if preview}
    <p class="text-sm opacity-75 leading-relaxed line-clamp-3" style="margin:0;">
        {previewText}
    </p>
{:else}
    <div class="prose prose-sm max-w-none prose-slate dark:prose-invert">
        {@html html}
    </div>
{/if}
