/**
 * AP Diagnostic Mode Component - Alpine.js Component
 *
 * Handles the Live/Diagnostic mode toggle and timer display.
 * Uses $store.apDetails for state.
 *
 * Usage:
 *   <div x-data="apDiagnosticMode()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('apDiagnosticMode', () => ({
        // --- Computed bindings to store ---
        get isActive() {
            return Alpine.store('apDetails').isDiagnosticActive;
        },

        get timerDisplay() {
            return Alpine.store('apDetails').diagnosticTimerDisplay;
        },

        get isLoading() {
            return Alpine.store('apDetails').isLoading;
        },

        // --- Actions ---
        toggleMode(event) {
            const isChecked = event.target.checked;
            if (isChecked) {
                Alpine.store('apDetails').startDiagnosticMode();
            } else {
                Alpine.store('apDetails').stopDiagnosticMode(true);
            }
        }
    }));

    console.log('[Component] ApDiagnosticMode initialized');
});
