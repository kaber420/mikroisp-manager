<script lang="ts">
    import { notify } from "$lib/stores/notifications";
    import { updateSettings, restartBots } from "$lib/api";

    // Propiedades usando runas de Svelte 5
    let {
        generalSettings = $bindable({}),
    } = $props<{
        generalSettings: Record<string, string>;
    }>();

    let botSaving = $state(false);
    let botRestarting = $state(false);

    function getS(key: string) {
        return generalSettings[key] ?? "";
    }
    function setS(key: string, val: string) {
        generalSettings = { ...generalSettings, [key]: val };
    }

    async function saveBotSettings() {
        botSaving = true;
        try {
            await updateSettings(generalSettings);
            notify.success("Configuración de bots guardada");
        } catch {
            notify.error("Error al guardar bots");
        } finally {
            botSaving = false;
        }
    }

    async function onRestartBots() {
        botRestarting = true;
        try {
            await updateSettings(generalSettings);
            const res = await restartBots();
            notify.success(res.message);
        } catch {
            notify.error("Error al reiniciar bots");
        } finally {
            botRestarting = false;
        }
    }
</script>

<div class="card bg-base-100 shadow-xl border border-base-200">
    <div class="card-body space-y-8">
        <!-- TOKENS Y MODO -->
        <section>
            <h2
                class="text-lg font-semibold mb-1 flex items-center gap-2"
            >
                🔑 Tokens y Modo de Ejecución
            </h2>
            <p class="text-sm text-base-content/60 mb-4">
                Configura los tokens de Telegram y el modo de operación.
            </p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="form-control">
                    <label class="label" for="bot_execution_mode"
                        ><span class="label-text"
                            >Modo de Ejecución</span
                        ></label
                    >
                    <select
                        id="bot_execution_mode"
                        class="select select-bordered"
                        value={getS("bot_execution_mode")}
                        onchange={(e) =>
                            setS(
                                "bot_execution_mode",
                                (e.target as HTMLSelectElement).value,
                            )}
                    >
                        <option value="auto"
                            >⚡ Auto (Recomendado)</option
                        >
                        <option value="polling"
                            >🔄 Polling (Interno)</option
                        >
                        <option value="webhook"
                            >🌐 Webhook (Dominio/Túnel)</option
                        >
                    </select>
                </div>
                <div class="form-control">
                    <label class="label" for="bot_external_url"
                        ><span class="label-text"
                            >URL Externa (para Webhook)</span
                        ></label
                    >
                    <input
                        id="bot_external_url"
                        type="text"
                        class="input input-bordered"
                        placeholder="https://mi-dominio.com"
                        value={getS("bot_external_url")}
                        oninput={(e) =>
                            setS(
                                "bot_external_url",
                                (e.target as HTMLInputElement).value,
                            )}
                    />
                </div>
                <div class="form-control">
                    <label class="label" for="telegram_bot_token"
                        ><span class="label-text"
                            >Token Bot Técnicos/Alertas</span
                        ></label
                    >
                    <input
                        id="telegram_bot_token"
                        type="password"
                        class="input input-bordered"
                        placeholder="123456:ABC-DEF..."
                        value={getS("telegram_bot_token")}
                        oninput={(e) =>
                            setS(
                                "telegram_bot_token",
                                (e.target as HTMLInputElement).value,
                            )}
                    />
                </div>
                <div class="form-control">
                    <label class="label" for="client_bot_token"
                        ><span class="label-text"
                            >Token Bot Clientes</span
                        ></label
                    >
                    <input
                        id="client_bot_token"
                        type="password"
                        class="input input-bordered"
                        placeholder="123456:ABC-DEF..."
                        value={getS("client_bot_token")}
                        oninput={(e) =>
                            setS(
                                "client_bot_token",
                                (e.target as HTMLInputElement).value,
                            )}
                    />
                </div>
                <div class="form-control">
                    <label class="label" for="telegram_chat_id"
                        ><span class="label-text"
                            >Chat ID de Alertas</span
                        ></label
                    >
                    <input
                        id="telegram_chat_id"
                        type="text"
                        class="input input-bordered"
                        placeholder="-123456789"
                        value={getS("telegram_chat_id")}
                        oninput={(e) =>
                            setS(
                                "telegram_chat_id",
                                (e.target as HTMLInputElement).value,
                            )}
                    />
                </div>
            </div>
        </section>

        <div class="divider"></div>

        <!-- MENSAJES DE BIENVENIDA -->
        <section>
            <h2 class="text-lg font-semibold mb-1">
                💬 Mensajes de Bienvenida
            </h2>
            <p class="text-sm text-base-content/60 mb-4">
                Personaliza los mensajes iniciales del bot.
            </p>
            <div class="grid grid-cols-1 gap-4">
                <div class="form-control">
                    <label class="label" for="bot_welcome_msg_client"
                        ><span class="label-text"
                            >Saludo (Cliente vinculado)</span
                        ></label
                    >
                    <textarea
                        id="bot_welcome_msg_client"
                        class="textarea textarea-bordered font-mono text-sm"
                        rows="3"
                        value={getS("bot_welcome_msg_client")}
                        oninput={(e) =>
                            setS(
                                "bot_welcome_msg_client",
                                (e.target as HTMLTextAreaElement).value,
                            )}
                    ></textarea>
                </div>
                <div class="form-control">
                    <label class="label" for="bot_welcome_msg_guest"
                        ><span class="label-text"
                            >Saludo (Invitado — debe incluir {"{user_id}"})</span
                        ></label
                    >
                    <textarea
                        id="bot_welcome_msg_guest"
                        class="textarea textarea-bordered font-mono text-sm"
                        rows="4"
                        value={getS("bot_welcome_msg_guest")}
                        oninput={(e) =>
                            setS(
                                "bot_welcome_msg_guest",
                                (e.target as HTMLTextAreaElement).value,
                            )}
                    ></textarea>
                </div>
                <div class="form-control">
                    <label class="label" for="bot_auto_reply_msg"
                        ><span class="label-text"
                            >Mensaje Automático (sin sesión activa)</span
                        ></label
                    >
                    <textarea
                        id="bot_auto_reply_msg"
                        class="textarea textarea-bordered font-mono text-sm"
                        rows="3"
                        value={getS("bot_auto_reply_msg")}
                        oninput={(e) =>
                            setS(
                                "bot_auto_reply_msg",
                                (e.target as HTMLTextAreaElement).value,
                            )}
                    ></textarea>
                </div>
            </div>
        </section>

        <div class="divider"></div>

        <!-- BOTONES DEL MENÚ -->
        <section>
            <h2 class="text-lg font-semibold mb-1">
                🎛️ Botones del Menú Principal
            </h2>
            <p class="text-sm text-base-content/60 mb-4">
                Activa/desactiva y personaliza el texto de cada botón.
            </p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {#each [{ label: "Reportar Falla", enableKey: "bot_enable_btn_report", valueKey: "bot_val_btn_report" }, { label: "Ver Tickets", enableKey: "bot_enable_btn_status", valueKey: "bot_val_btn_status" }, { label: "Clave WiFi", enableKey: "bot_enable_btn_wifi", valueKey: "bot_val_btn_wifi" }, { label: "Agente Humano", enableKey: "bot_enable_btn_agent", valueKey: "bot_val_btn_agent" }] as btn}
                    <div class="p-3 border border-base-200 rounded-lg">
                        <div
                            class="flex items-center justify-between mb-2"
                        >
                            <span class="text-sm font-medium"
                                >{btn.label}</span
                            >
                            <input
                                type="checkbox"
                                class="toggle toggle-primary toggle-sm"
                                checked={getS(btn.enableKey) === "true"}
                                onchange={(e) =>
                                    setS(
                                        btn.enableKey,
                                        String(
                                            (
                                                e.target as HTMLInputElement
                                            ).checked,
                                        ),
                                    )}
                            />
                        </div>
                        <input
                            type="text"
                            class="input input-bordered input-sm w-full"
                            disabled={getS(btn.enableKey) !== "true"}
                            value={getS(btn.valueKey)}
                            oninput={(e) =>
                                setS(
                                    btn.valueKey,
                                    (e.target as HTMLInputElement)
                                        .value,
                                )}
                        />
                    </div>
                {/each}
            </div>
        </section>
    </div>

    <div
        class="border-t border-base-200 px-6 py-4 flex justify-between items-center"
    >
        <button
            class="btn btn-warning gap-2"
            onclick={onRestartBots}
            disabled={botRestarting || botSaving}
        >
            {#if botRestarting}<span
                    class="loading loading-spinner loading-sm"
                ></span>{:else}🔁{/if}
            {botRestarting
                ? "Reiniciando..."
                : "Aplicar y Reiniciar Bots"}
        </button>
        <button
            class="btn btn-primary"
            onclick={saveBotSettings}
            disabled={botSaving}
        >
            {#if botSaving}<span
                    class="loading loading-spinner loading-sm"
                ></span>{/if}
            Guardar Cambios
        </button>
    </div>
</div>
