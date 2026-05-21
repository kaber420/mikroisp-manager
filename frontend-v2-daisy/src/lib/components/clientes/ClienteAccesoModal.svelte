<script lang="ts">
    import type { User } from '$lib/types/user';

    interface AccessPayload {
        username: string;
        password: string | undefined;
        telegram_chat_id: string | null;
    }

    interface Props {
        open: boolean;
        clientUser: User | null;
        clientEmail: string;
        clientName: string;
        clientTelegram: string;
        creatingAccess: boolean;
        accessError: string;
        onsubmit: (payload: AccessPayload) => void;
        onclose: () => void;
    }

    let {
        open,
        clientUser,
        clientEmail,
        clientName,
        clientTelegram,
        creatingAccess,
        accessError,
        onsubmit,
        onclose,
    }: Props = $props();

    let username = $state('');
    let password = $state('');
    let telegramChatId = $state('');

    // Pre-fill form when modal opens
    $effect(() => {
        if (open) {
            if (clientUser) {
                username = clientUser.username;
                telegramChatId = clientUser.telegram_chat_id || '';
                password = '';
            } else {
                username = clientEmail?.split('@')[0] || clientName.toLowerCase().replace(/\s+/g, '.');
                telegramChatId = clientTelegram || '';
                password = '';
            }
        }
    });

    function handleSubmit(e: SubmitEvent) {
        e.preventDefault();
        onsubmit({
            username,
            password: password || undefined,
            telegram_chat_id: telegramChatId || null,
        });
    }
</script>

{#if open}
    <div style="position:fixed;inset:0;z-index:1000;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(0,0,0,0.6);">
        <div class="glass-card-flat" style="border-radius:1rem;width:100%;max-width:460px;overflow:hidden;">
            <div style="padding:1.25rem 1.5rem;font-weight:700;font-size:1.1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);display:flex;justify-content:space-between;align-items:center;">
                <span>{clientUser ? 'Gestionar' : 'Crear'} Acceso al Portal</span>
                <button class="btn btn-ghost btn-xs btn-circle" onclick={onclose}>✕</button>
            </div>
            <form onsubmit={handleSubmit} style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;">
                <div class="form-control">
                    <label class="label"><span class="label-text">Nombre de Usuario</span></label>
                    <input type="text" bind:value={username} required class="input input-bordered" placeholder="Ej: pablo.perez" />
                </div>
                <div class="form-control">
                    <label class="label">
                        <span class="label-text">Contraseña</span>
                        {#if clientUser}
                            <span class="label-text-alt text-warning">Dejar vacío para no cambiar</span>
                        {/if}
                    </label>
                    <input type="password" bind:value={password} required={!clientUser} class="input input-bordered" placeholder="••••••••" />
                </div>
                <div class="form-control">
                    <label class="label">
                        <span class="label-text">Telegram Chat ID</span>
                        <span class="label-text-alt text-info">Para comandos /password</span>
                    </label>
                    <input type="text" bind:value={telegramChatId} class="input input-bordered" placeholder="Ej: 123456789" />
                </div>

                {#if accessError}
                    <div class="alert alert-error p-2 text-sm"><span>{accessError}</span></div>
                {/if}

                <div style="display:flex;justify-content:flex-end;gap:0.75rem;padding-top:1rem;">
                    <button type="button" class="btn btn-ghost" onclick={onclose}>Cancelar</button>
                    <button type="submit" class="btn btn-primary" disabled={creatingAccess}>
                        {#if creatingAccess}<span class="loading loading-spinner loading-xs"></span>{/if}
                        {clientUser ? 'Guardar Cambios' : 'Habilitar Acceso'}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}
