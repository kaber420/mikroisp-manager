<script lang="ts">
    let {
        message = $bindable(""),
    }: {
        message: string;
    } = $props();
</script>

<div class="card bg-base-100 shadow-sm">
    <div class="card-body gap-3">
        <h2 class="card-title text-base">
            <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-primary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
            </svg>
            Mensaje
        </h2>

        <div class="relative">
            <textarea
                bind:value={message}
                rows="7"
                placeholder="Escribe el mensaje que recibirán tus destinatarios..."
                class="textarea textarea-bordered w-full resize-none pr-16 font-mono text-sm leading-relaxed"
            ></textarea>
            <span
                class="text-base-content/40 absolute right-3 bottom-3 select-none text-xs tabular-nums"
            >
                {message.length} car.
            </span>
        </div>

        <div class="text-base-content/40 flex gap-1 text-xs">
            <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-3.5 w-3.5 shrink-0 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
            </svg>
            Telegram admite <strong>Markdown</strong>: *negrita*,
            _cursiva_, `código`
        </div>
    </div>
</div>
