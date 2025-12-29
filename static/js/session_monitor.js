/**
 * Session Monitor - Idle Detection and Auto-Logout
 * 
 * Tracks user activity and shows a warning modal after 10 minutes of inactivity.
 * If no activity for 3 more minutes, automatically logs out.
 */

(function () {
    'use strict';

    // Configuration (in seconds)
    const IDLE_WARNING_TIME = 10 * 60;  // 10 minutes until warning
    const IDLE_LOGOUT_TIME = 13 * 60;   // 13 minutes until logout (10 + 3)
    const CHECK_INTERVAL = 1000;        // Check every second

    let lastActivityTime = Date.now();
    let warningModalVisible = false;
    let countdownInterval = null;

    /**
     * Reset the idle timer on user activity
     */
    function resetIdleTimer() {
        lastActivityTime = Date.now();
        if (warningModalVisible) {
            hideWarningModal();
        }
    }

    /**
     * Get the warning modal element
     */
    function getWarningModal() {
        return document.getElementById('session-warning-modal');
    }

    /**
     * Get the countdown display element
     */
    function getCountdownDisplay() {
        return document.getElementById('session-countdown');
    }

    /**
     * Show the warning modal
     */
    function showWarningModal() {
        const modal = getWarningModal();
        if (modal && !warningModalVisible) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            warningModalVisible = true;
            startCountdown();
        }
    }

    /**
     * Hide the warning modal
     */
    function hideWarningModal() {
        const modal = getWarningModal();
        if (modal && warningModalVisible) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            warningModalVisible = false;
            stopCountdown();
        }
    }

    /**
     * Start the countdown timer display
     */
    function startCountdown() {
        const countdownDisplay = getCountdownDisplay();
        if (!countdownDisplay) return;

        countdownInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - lastActivityTime) / 1000);
            const remaining = IDLE_LOGOUT_TIME - elapsed;

            if (remaining <= 0) {
                performLogout();
                return;
            }

            const minutes = Math.floor(remaining / 60);
            const seconds = remaining % 60;
            countdownDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    /**
     * Stop the countdown timer
     */
    function stopCountdown() {
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
        }
    }

    /**
     * Perform logout by redirecting to logout endpoint
     */
    function performLogout() {
        stopCountdown();
        window.location.href = '/logout';
    }

    /**
     * Check idle status and show/hide modal accordingly
     */
    function checkIdleStatus() {
        const elapsed = Math.floor((Date.now() - lastActivityTime) / 1000);

        if (elapsed >= IDLE_LOGOUT_TIME) {
            performLogout();
        } else if (elapsed >= IDLE_WARNING_TIME && !warningModalVisible) {
            showWarningModal();
        }
    }

    /**
     * Initialize the session monitor
     */
    function init() {
        // Track user activity events
        const activityEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];

        activityEvents.forEach(event => {
            document.addEventListener(event, resetIdleTimer, { passive: true });
        });

        // Start checking idle status
        setInterval(checkIdleStatus, CHECK_INTERVAL);

        // Handle "Stay Logged In" button click
        const stayLoggedInBtn = document.getElementById('session-stay-btn');
        if (stayLoggedInBtn) {
            stayLoggedInBtn.addEventListener('click', () => {
                resetIdleTimer();
            });
        }

        console.log('🔒 Session Monitor initialized (Warning: 10min, Logout: 13min)');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
