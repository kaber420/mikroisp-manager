<script lang="ts">
    import type { TicketStatus } from "$lib/types/ticket";

    interface Props {
        updatingStatus: boolean;
        onChangeStatus: (status: TicketStatus) => void;
    }

    let { updatingStatus, onChangeStatus }: Props = $props();
</script>

<div class="dropdown dropdown-end">
    <div
        tabindex="0"
        role="button"
        class="btn btn-sm btn-ghost border border-base-300"
        class:loading={updatingStatus}
    >
        {updatingStatus ? "" : "Cambiar estado"}
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
        >
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
    </div>
    <ul class="dropdown-content z-[50] menu p-2 shadow-xl bg-base-200 rounded-box w-48 border border-base-300">
        <li>
            <button onclick={() => onChangeStatus("open")}>
                <span class="badge badge-success badge-xs"></span> Abierto
            </button>
        </li>
        <li>
            <button onclick={() => onChangeStatus("pending")}>
                <span class="badge badge-warning badge-xs"></span> Pendiente
            </button>
        </li>
        <li>
            <button onclick={() => onChangeStatus("resolved")}>
                <span class="badge badge-primary badge-xs"></span> Resuelto
            </button>
        </li>
        <li class="divider my-0.5"></li>
        <li>
            <button onclick={() => onChangeStatus("closed")} class="text-error">
                <span class="badge badge-error badge-xs"></span> Cerrado
            </button>
        </li>
    </ul>
</div>
