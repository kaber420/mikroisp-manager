/**
 * Shared Provisioning Mixin for Alpine.js
 * 
 * Usage in Alpine components:
 *   Alpine.data('myComponent', () => ({
 *       ...provisionMixin,
 *       // your component data...
 *   }))
 */
const provisionMixin = {
    // --- Provisioning State ---
    isProvisionModalOpen: false,
    isProvisioning: false,
    provisionError: '',
    provisionSuccess: '',
    provisionDeviceType: 'Device',  // 'Router' or 'AP'
    provisionApiPath: '/api/routers',  // or '/api/aps'
    currentProvisionTarget: {
        host: '',
        hostname: '',
        newUser: 'umanager_api',
        newPass: '',
        method: 'ssh'
    },

    // --- Provisioning Methods ---

    /**
     * Open the provision modal for a device
     * @param {Object} device - The device object (router or ap)
     * @param {string} deviceType - 'Router' or 'AP'
     * @param {string} apiPath - API base path, e.g. '/api/routers' or '/api/aps'
     */
    openProvisionModal(device, deviceType = 'Device', apiPath = '/api/routers') {
        this.currentProvisionTarget = {
            host: device.host,
            hostname: device.hostname || device.host,
            newUser: 'umanager_api',
            newPass: this.generateSecurePassword(),
            method: 'ssh'
        };
        this.provisionDeviceType = deviceType;
        this.provisionApiPath = apiPath;
        this.provisionError = '';
        this.provisionSuccess = '';
        this.isProvisioning = false;
        this.isProvisionModalOpen = true;
    },

    closeProvisionModal() {
        this.isProvisionModalOpen = false;
        this.provisionError = '';
        this.provisionSuccess = '';
    },

    generateSecurePassword(length = 16) {
        const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$%';
        let password = '';
        for (let i = 0; i < length; i++) {
            password += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return password;
    },

    generatePassword() {
        this.currentProvisionTarget.newPass = this.generateSecurePassword();
    },

    async handleProvisionSubmit() {
        if (!this.currentProvisionTarget.newUser || !this.currentProvisionTarget.newPass) {
            this.provisionError = 'Username and password are required.';
            return;
        }

        this.isProvisioning = true;
        this.provisionError = '';
        this.provisionSuccess = '';

        try {
            const url = `${this.provisionApiPath}/${encodeURIComponent(this.currentProvisionTarget.host)}/provision`;

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    new_api_user: this.currentProvisionTarget.newUser,
                    new_api_password: this.currentProvisionTarget.newPass,
                    method: this.currentProvisionTarget.method
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Provisioning failed');
            }

            this.provisionSuccess = data.message || `${this.provisionDeviceType} provisioned successfully!`;

            // Refresh data after successful provisioning
            setTimeout(async () => {
                if (typeof this.loadInitialData === 'function') {
                    await this.loadInitialData();
                }
                this.closeProvisionModal();
            }, 1500);

        } catch (error) {
            console.error('Provisioning error:', error);
            this.provisionError = error.message;
        } finally {
            this.isProvisioning = false;
        }
    }
};

// Make available globally for Alpine components
window.provisionMixin = provisionMixin;
