<script lang="ts">
    interface Notification {
        id: number;
        msg: string;
        type: string;
    }
    
    let notifications = $state<Notification[]>([]);

    export function addNotification(msg: string, type = 'info') {
        const id = Date.now();
        notifications = [...notifications, { id, msg, type }];
        setTimeout(() => {
            notifications = notifications.filter(n => n.id !== id);
        }, 5000);
    }
</script>

<div class="toast toast-end toast-bottom z-[100]">
    {#each notifications as n (n.id)}
        <div class="alert alert-{n.type} shadow-lg animate-in fade-in slide-in-from-right">
            <span>{n.msg}</span>
        </div>
    {/each}
</div>
