<script lang="ts">
    import { onMount } from 'svelte';
    import { clearSession } from '../authutils';

    let { timeoutMinutes = 30, warningMinutes = 5 } = $props();

    let timeLeft = $state(0);
    let showWarning = $state(false);

    $effect(() => {
        if (timeLeft === 0) timeLeft = timeoutMinutes * 60;
    });

    onMount(() => {
        const interval = setInterval(() => {
            timeLeft -= 1;
            if (timeLeft <= warningMinutes * 60) {
                showWarning = true;
            }
            if (timeLeft <= 0) {
                clearSession();
                window.location.href = '/login?reason=timeout';
            }
        }, 1000);

        return () => clearInterval(interval);
    });

    function resetTimer() {
        timeLeft = timeoutMinutes * 60;
        showWarning = false;
    }
</script>

{#if showWarning}
<div class="toast toast-top toast-center z-[100]">
    <div class="alert alert-warning shadow-2xl flex-col items-start gap-4 p-6 min-w-80 border-2 border-warning/20">
        <div class="flex items-center gap-3">
            <span class="text-2xl animate-pulse">⏳</span>
            <div>
                <h3 class="font-bold text-lg">Sesión por expirar</h3>
                <p class="text-xs opacity-70">Tu sesión se cerrará en menos de {warningMinutes} minutos.</p>
            </div>
        </div>
        <button class="btn btn-sm btn-block btn-primary" onclick={resetTimer}>
            Mantener sesión activa
        </button>
    </div>
</div>
{/if}
