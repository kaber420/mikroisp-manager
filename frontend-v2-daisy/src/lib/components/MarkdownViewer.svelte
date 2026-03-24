<script lang="ts">
    import { marked } from 'marked';
    import DOMPurify from 'isomorphic-dompurify';

    let { content = "" } = $props<{ content: string }>();

    let html = $derived(DOMPurify.sanitize(marked.parse(content) as string));
</script>

<div class="prose prose-sm max-w-none prose-slate dark:prose-invert">
    {@html html}
</div>
