"use strict";
function openEmail(source = "default") {
  const email = "info@4devnet.com";
  let subject = "";
  let body = "";

  // Determine source if not explicitly provided
  if (source === "default") {
    const button =
      event?.target?.closest(".button-1") ||
      event?.target?.closest(".email-box");
    if (button) {
      if (button.classList.contains("button-1")) {
        source = "social";
      } else if (button.classList.contains("email-box")) {
        source = "contact";
      }
    }
  }

  // Set subject and body based on source
  if (source === "contact") {
    subject = "Inquiry about Odoo 18 India Mart Integration";
    body =
      "Hello,\n\nI am interested in your Odoo 18 India Mart Integration services.\n\nPlease provide more information.\n\nThank you.";
  }
  // For 'social' source, subject and body remain empty

  // Create mailto link
  let mailtoLink = `mailto:${email}`;
  if (subject || body) {
    const params = new URLSearchParams();
    if (subject) params.append("subject", subject);
    if (body) params.append("body", body);
    mailtoLink += `?${params.toString()}`;
  }

  // Add visual feedback if button exists
  const button =
    event?.target?.closest(".button-1") || event?.target?.closest(".email-box");
  if (button) {
    button.style.transform = "scale(0.95)";
    setTimeout(() => {
      button.style.transform = "";
    }, 150);
  }

  // Open email client
  window.location.href = mailtoLink;
}

// Alternative approach: Separate functions for clarity
function openEmailFromSocial() {
  const email = "info@4devnet.com";
  const mailtoLink = `mailto:${email}`;

  // Add visual feedback
  const button = event?.target?.closest(".button-1");
  if (button) {
    button.style.transform = "scale(0.95)";
    setTimeout(() => {
      button.style.transform = "";
    }, 150);
  }

  // Open email client with empty subject and body
  window.location.href = mailtoLink;
}

function openEmailFromContact() {
  const email = "info@4devnet.com";
  const subject = "Inquiry about Odoo 18 India Mart Integration";
  const body =
    "Hello,\n\nI am interested in your Odoo 18 India Mart Integration services.\n\nPlease provide more information.\n\nThank you.";

  // Create mailto link with predefined content
  const mailtoLink = `mailto:${email}?subject=${encodeURIComponent(
    subject
  )}&body=${encodeURIComponent(body)}`;

  // Add visual feedback
  const button = event?.target?.closest(".email-box");
  if (button) {
    button.style.transform = "scale(0.95)";
    setTimeout(() => {
      button.style.transform = "";
    }, 150);
  }

  // Open email client
  window.location.href = mailtoLink;
}

// Phone functionality (for contact section boxes)
function openPhone() {
  const phoneNumber = "+918780674399";

  // Check if device supports tel: protocol (mobile devices)
  if (
    /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    )
  ) {
    // Mobile device - open phone dialer
    window.location.href = `tel:${phoneNumber}`;
  } else {
    // Desktop - copy to clipboard and show notification
    navigator.clipboard
      .writeText(phoneNumber)
      .then(function () {
        showNotification(
          '<i class="fas fa-check-circle" style="color: #4ade80; margin-right: 8px;"></i>Phone number copied to clipboard!',
          "linear-gradient(135deg, #0a1425, #1a2a40)"
        );
      })
      .catch(function () {
        // Fallback if clipboard API fails
        alert(`Phone number: ${phoneNumber}`);
      });
  }
}

// WhatsApp functionality (for social links section)
function openWhatsApp() {
  const phoneNumber = "918780674399"; // Without + for WhatsApp
  const defaultMessage =
    "Hello! I am interested in your Odoo 18 India Mart Integration services. Could you please provide more information about your offerings?";

  // Add visual feedback
  const button = event?.target?.closest(".button-3");
  if (button) {
    button.style.transform = "scale(0.95)";
    setTimeout(() => {
      button.style.transform = "";
    }, 150);
  }

  // Check if device is mobile
  const isMobile =
    /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    );

  if (isMobile) {
    // Mobile device - open WhatsApp app
    const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(
      defaultMessage
    )}`;
    window.open(whatsappUrl, "_blank");
  } else {
    // Desktop - open WhatsApp Web
    const whatsappWebUrl = `https://web.whatsapp.com/send?phone=${phoneNumber}&text=${encodeURIComponent(
      defaultMessage
    )}`;
    window.open(whatsappWebUrl, "_blank");
  }
}

// Skype functionality (for social links section)
function openSkype() {
  // Add visual feedback
  const button = event?.target?.closest(".button-2");
  if (button) {
    button.style.transform = "scale(0.95)";
    setTimeout(() => {
      button.style.transform = "";
    }, 150);
  }

  // Show coming soon notification
  showNotification(
    '<i class="fab fa-skype" style="margin-right: 8px;"></i>Skype feature coming soon!',
    "linear-gradient(135deg, #00aff0, #0099d4)"
  );
}

// ===================================
// UTILITY FUNCTIONS
// ===================================

// Reusable notification function
function showNotification(
  message,
  background = "linear-gradient(135deg, #0a1425, #1a2a40)"
) {
  const notification = document.createElement("div");
  notification.innerHTML = `
    <div style="
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${background};
      color: white;
      padding: 15px 20px;
      border-radius: 10px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
      z-index: 10000;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      border: 1px solid rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(10px);
      animation: slideInRight 0.3s ease-out;
    ">
      ${message}
    </div>
  `;

  document.body.appendChild(notification);

  // Remove notification after 3 seconds
  setTimeout(() => {
    if (document.body.contains(notification)) {
      notification.style.animation = "slideOutRight 0.3s ease-in";
      setTimeout(() => {
        if (document.body.contains(notification)) {
          document.body.removeChild(notification);
        }
      }, 300);
    }
  }, 3000);
}

// ===================================
// KEYBOARD ACCESSIBILITY
// ===================================

document.addEventListener("keydown", function (event) {
  if (event.key === "Enter" || event.key === " ") {
    const activeElement = document.activeElement;

    if (activeElement.classList.contains("button-1")) {
      event.preventDefault();
      openEmailFromSocial();
    } else if (activeElement.classList.contains("email-box")) {
      event.preventDefault();
      openEmailFromContact();
    } else if (activeElement.classList.contains("button-2")) {
      event.preventDefault();
      openSkype();
    } else if (activeElement.classList.contains("button-3")) {
      event.preventDefault();
      openWhatsApp();
    } else if (activeElement.classList.contains("phone-box")) {
      event.preventDefault();
      openPhone();
    }
  }
});

// ===================================
// NOTIFICATION ANIMATIONS
// ===================================

// Add CSS animations for notifications
const style = document.createElement("style");
style.textContent = `
  @keyframes slideInRight {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  @keyframes slideOutRight {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(100%);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

// ===================================
// INITIALIZATION
// ===================================

// ===================================
// SCREENSHOT MODAL FUNCTIONALITY
// ===================================

let currentImageSrc = "";
let currentImageTitle = "";

// Open screenshot modal
function openScreenshotModal(imageSrc, title, description) {
  const modal = document.getElementById("screenshotModal");
  const modalImage = document.getElementById("modalImage");
  const modalTitle = document.getElementById("modalTitle");
  const modalDescription = document.getElementById("modalDescription");

  // Store current image info for download
  currentImageSrc = imageSrc;
  currentImageTitle = title;

  // Set modal content
  modalImage.src = imageSrc;
  modalImage.alt = title;
  modalTitle.textContent = title;
  modalDescription.textContent = description;

  // Show modal
  modal.classList.add("active");
  document.body.style.overflow = "hidden"; // Prevent background scrolling

  // Focus on close button for accessibility
  setTimeout(() => {
    document.querySelector(".close-btn").focus();
  }, 100);

  // Add escape key listener
  document.addEventListener("keydown", handleEscapeKey);
}

// Close screenshot modal
function closeScreenshotModal() {
  const modal = document.getElementById("screenshotModal");
  const modalContent = document.querySelector(".modal-content");

  // Add closing animation
  modalContent.style.animation = "modalSlideOut 0.3s ease-in";

  setTimeout(() => {
    modal.classList.remove("active");
    document.body.style.overflow = ""; // Restore scrolling
    modalContent.style.animation = ""; // Reset animation

    // Clear image src to prevent flash
    document.getElementById("modalImage").src = "";
  }, 300);

  // Remove escape key listener
  document.removeEventListener("keydown", handleEscapeKey);
}

// Handle escape key press
function handleEscapeKey(event) {
  if (event.key === "Escape") {
    closeScreenshotModal();
  }
}

// Download image function
function downloadImage() {
  if (!currentImageSrc) return;

  // Create a temporary link element
  const link = document.createElement("a");
  link.href = currentImageSrc;
  link.download = `${currentImageTitle.replace(/\s+/g, "_")}.jpeg`;

  // Trigger download
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Show download notification
  showNotification(
    '<i class="fas fa-download" style="color: #4ade80; margin-right: 8px;"></i>Screenshot downloaded successfully!',
    "linear-gradient(135deg, #10b981, #059669)"
  );
}

// Enhanced notification function for screenshots
function showScreenshotNotification(message, type = "success") {
  const backgrounds = {
    success: "linear-gradient(135deg, #10b981, #059669)",
    error: "linear-gradient(135deg, #ef4444, #dc2626)",
    info: "linear-gradient(135deg, #3b82f6, #2563eb)",
  };

  const notification = document.createElement("div");
  notification.innerHTML = `
    <div style="
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${backgrounds[type]};
      color: white;
      padding: 15px 20px;
      border-radius: 10px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
      z-index: 10001;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      border: 1px solid rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(10px);
      animation: slideInRight 0.3s ease-out;
      max-width: 300px;
    ">
      ${message}
    </div>
  `;

  document.body.appendChild(notification);

  // Remove notification after 3 seconds
  setTimeout(() => {
    if (document.body.contains(notification)) {
      notification.style.animation = "slideOutRight 0.3s ease-in";
      setTimeout(() => {
        if (document.body.contains(notification)) {
          document.body.removeChild(notification);
        }
      }, 300);
    }
  }, 3000);
}

// ===================================
// ENHANCED ACCESSIBILITY
// ===================================

// Add keyboard navigation for screenshot cards
document.addEventListener("DOMContentLoaded", function () {
  const screenshots = document.querySelectorAll(".screen-shot");

  screenshots.forEach((screenshot, index) => {
    // Make screenshots focusable
    screenshot.setAttribute("tabindex", "0");
    screenshot.setAttribute("role", "button");
    screenshot.setAttribute(
      "aria-label",
      `View ${screenshot.querySelector(".ss-heading").textContent} in full size`
    );

    // Add keyboard support
    screenshot.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        screenshot.click();
      }
    });

    // Add focus styles
    screenshot.addEventListener("focus", function () {
      this.style.outline = "3px solid #7f54b3";
      this.style.outlineOffset = "2px";
    });

    screenshot.addEventListener("blur", function () {
      this.style.outline = "";
      this.style.outlineOffset = "";
    });
  });
});

// ===================================
// TOUCH GESTURES FOR MOBILE
// ===================================

let touchStartY = 0;
let touchEndY = 0;

// Add swipe to close functionality
document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("screenshotModal");

  modal.addEventListener("touchstart", function (event) {
    touchStartY = event.changedTouches[0].screenY;
  });

  modal.addEventListener("touchend", function (event) {
    touchEndY = event.changedTouches[0].screenY;
    handleSwipe();
  });

  function handleSwipe() {
    const swipeDistance = touchStartY - touchEndY;
    const minSwipeDistance = 100;

    // Swipe up to close
    if (swipeDistance > minSwipeDistance) {
      closeScreenshotModal();
    }
  }
});

// ===================================
// IMAGE LOADING OPTIMIZATION
// ===================================

// Preload images for better performance
function preloadImages() {
  const imageUrls = [
    "./Assets/Screenshots/Menu.jpeg",
    "./Assets/Screenshots/India-mart-integration.jpeg",
    "./Assets/Screenshots/ind-mart-general-setting.jpeg",
    "./Assets/Screenshots/Ind-mart-date-setting.jpeg",
    "./Assets/Screenshots/Sales-log.jpeg",
    "./Assets/Screenshots/Sales-report.jpeg",
  ];

  imageUrls.forEach((url) => {
    const img = new Image();
    img.src = url;
  });
}

// Initialize preloading when page loads
document.addEventListener("DOMContentLoaded", preloadImages);
