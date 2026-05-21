<script lang="ts">
    import type { User } from '$lib/types/user';

    interface Props {
        clientUser: User | null;
        accessLoading: boolean;
        onopenmodal: () => void;
    }

    let { clientUser, accessLoading, onopenmodal }: Props = $props();
</script>

<div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
    <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);">
        Gestión de Acceso al Portal
    </div>
    <div style="padding:2rem;display:flex;flex-direction:column;align-items:center;text-align:center;gap:1.5rem;">
        {#if accessLoading}
            <span class="loading loading-spinner loading-lg"></span>
        {:else if clientUser}
            <div class="avatar placeholder">
                <div class="bg-neutral text-neutral-content rounded-full w-24">
                    <span class="text-3xl">{clientUser.username[0].toUpperCase()}</span>
                </div>
            </div>
            <div>
                <h3 style="font-size:1.25rem;font-weight:700;margin:0;">{clientUser.username}</h3>
                <p style="opacity:0.6;margin:0.25rem 0;">{clientUser.email}</p>
                <div style="margin-top:0.5rem;display:flex;gap:0.5rem;justify-content:center;">
                    <span class="badge badge-success">Acceso Activo</span>
                    <span class="badge badge-outline">{clientUser.role}</span>
                </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-md mt-2">
                <div class="stats shadow bg-base-200/50">
                    <div class="stat p-3">
                        <div class="stat-title text-xs">Telegram ID</div>
                        <div class="stat-value text-sm">{clientUser.telegram_chat_id || 'No vinculado'}</div>
                    </div>
                </div>
                <div class="stats shadow bg-base-200/50">
                    <div class="stat p-3">
                        <div class="stat-title text-xs">Último Acceso</div>
                        <div class="stat-value text-sm">Próximamente</div>
                    </div>
                </div>
            </div>
            <button class="btn btn-outline btn-sm mt-4" onclick={onopenmodal}>
                Actualizar Credenciales / Telegram
            </button>
        {:else}
            <div style="background:color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 10%,transparent);padding:2rem;border-radius:50%;margin-bottom:0.5rem;">
                <svg class="w-16 h-16 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
            </div>
            <div>
                <h3 style="font-size:1.25rem;font-weight:700;">Sin Acceso al Portal</h3>
                <p style="opacity:0.6;max-width:400px;margin:0.5rem auto;">
                    Este cliente aún no tiene credenciales vinculadas para acceder al portal de autogestión.
                </p>
            </div>
            <button class="btn btn-primary" onclick={onopenmodal}>
                Crear Credenciales de Acceso
            </button>
        {/if}
    </div>
</div>
