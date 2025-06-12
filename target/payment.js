// Payment Processing Module - Mobile Bug Example
class PaymentProcessor {
    constructor() {
        this.isProcessing = false;
        this.form = document.getElementById('payment-form');
        this.submitButton = document.querySelector('.submit-btn');
        this.init();
    }

    init() {
        // Bug 1: No viewport meta tag handling - causes blank screens on mobile
        this.form.addEventListener('submit', this.handleSubmit.bind(this));
        
        // Bug 2: Mouse events only - doesn't work on touch devices
        this.submitButton.addEventListener('mousedown', this.onButtonPress.bind(this));
        this.submitButton.addEventListener('mouseup', this.onButtonRelease.bind(this));
    }

    handleSubmit(event) {
        event.preventDefault();
        
        // Bug 3: No mobile browser compatibility check
        if (!this.validateForm()) {
            return;
        }

        this.processPayment();
    }

    validateForm() {
        const cardNumber = document.getElementById('card-number').value;
        const expiry = document.getElementById('expiry').value;
        
        // Bug 4: No input validation for mobile keyboards
        // Mobile keyboards can introduce unexpected characters
        if (cardNumber.length < 16) {
            this.showError('Invalid card number');
            return false;
        }
        
        return true;
    }

    processPayment() {
        if (this.isProcessing) return;
        
        this.isProcessing = true;
        this.submitButton.disabled = true;
        
        // Bug 5: No error handling for mobile network issues
        fetch('/api/payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(this.getFormData())
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showSuccess('Payment successful!');
            } else {
                this.showError(data.message);
            }
        })
        .finally(() => {
            this.isProcessing = false;
            this.submitButton.disabled = false;
        });
    }

    getFormData() {
        return {
            cardNumber: document.getElementById('card-number').value,
            expiry: document.getElementById('expiry').value,
            cvv: document.getElementById('cvv').value,
            amount: document.getElementById('amount').value
        };
    }

    onButtonPress() {
        this.submitButton.classList.add('pressed');
    }

    onButtonRelease() {
        this.submitButton.classList.remove('pressed');
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        // Bug 6: Fixed positioning that breaks on mobile orientation change
        errorDiv.style.position = 'fixed';
        errorDiv.style.top = '10px';
        errorDiv.style.left = '10px';
        
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 3000);
    }

    showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        document.body.appendChild(successDiv);
        
        setTimeout(() => {
            successDiv.remove();
        }, 3000);
    }
}

// Bug 7: No mobile device detection or responsive initialization
document.addEventListener('DOMContentLoaded', () => {
    new PaymentProcessor();
});

// Bug 8: No touch event polyfills for older mobile browsers
// Bug 9: No handling for mobile-specific form validation errors
// Bug 10: CSS assumes desktop-first design without mobile breakpoints