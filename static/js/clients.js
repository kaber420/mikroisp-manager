/**
 * Clients Module - Entry Point
 * 
 * This file loads the modular components for the Clients page:
 * - ClientListStore: Global state for client list
 * - ClientListComponent: Table rendering and filtering
 * - ClientModalComponent: Create/Edit modal with service provisioning
 * 
 * Note: The individual files register themselves with Alpine on load.
 */

// The stores and components self-register on 'alpine:init'
// They are loaded via <script> tags in clients.html

// Additional initialization if needed
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Clients] Module loaded');
});