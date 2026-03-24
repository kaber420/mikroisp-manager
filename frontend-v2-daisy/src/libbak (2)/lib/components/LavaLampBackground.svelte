<script lang="ts">
    import { theme } from '../stores/theme';
</script>

{#if $theme.lavaLampActive}
<div class="fixed inset-0 -z-50 overflow-hidden bg-base-300 pointer-events-none">
    <!-- Animated Gradients for 'Lava Lamp' effect -->
    <div class="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary/20 rounded-full blur-[120px] animate-blob"></div>
    <div class="absolute top-[20%] right-[-10%] w-[40%] h-[60%] bg-secondary/15 rounded-full blur-[150px] animate-blob animation-delay-2000"></div>
    <div class="absolute bottom-[-10%] left-[20%] w-[60%] h-[40%] bg-accent/10 rounded-full blur-[100px] animate-blob animation-delay-4000"></div>
</div>
{/if}

<style>
    @keyframes blob {
        0% { transform: translate(0px, 0px) scale(1); }
        33% { transform: translate(30px, -50px) scale(1.1); }
        66% { transform: translate(-20px, 20px) scale(0.9); }
        100% { transform: translate(0px, 0px) scale(1); }
    }
    .animate-blob {
        animation: blob 20s infinite alternate;
    }
    .animation-delay-2000 { animation-delay: 2s; }
    .animation-delay-4000 { animation-delay: 4s; }
</style>
