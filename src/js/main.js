// Main JavaScript entry point for FindingModelForge
import Alpine from "alpinejs"
import { initFlowbite } from "flowbite"
import htmx from "htmx.org"

// Make Alpine and other libraries globally available
window.Alpine = Alpine
window.initFlowbite = initFlowbite
window.htmx = htmx

// Dark mode management
document.addEventListener("alpine:init", () => {
  Alpine.data("app", () => ({
    isDark: false,

    init() {
      // Get current state from DOM (already set by head script)
      this.isDark = document.documentElement.classList.contains("dark")

      // Listen for system theme changes
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", e => {
        if (!localStorage.getItem("darkMode")) {
          this.isDark = e.matches
          this.updateDarkMode()
        }
      })
    },

    toggleDarkMode() {
      this.isDark = !this.isDark
      localStorage.setItem("darkMode", this.isDark.toString())
      this.updateDarkMode()
    },

    updateDarkMode() {
      if (this.isDark) {
        document.documentElement.classList.add("dark")
      } else {
        document.documentElement.classList.remove("dark")
      }
    },
  }))
})

// Global dark mode toggle function (for navbar compatibility)
window.toggleDarkMode = function () {
  const isDark = document.documentElement.classList.contains("dark")
  if (isDark) {
    document.documentElement.classList.remove("dark")
    localStorage.setItem("darkMode", "false")
  } else {
    document.documentElement.classList.add("dark")
    localStorage.setItem("darkMode", "true")
  }

  // Update Alpine.js state if available
  if (window.Alpine && window.Alpine.store) {
    // Trigger any Alpine components to update their isDark state
    document.dispatchEvent(
      new CustomEvent("dark-mode-changed", {
        detail: { isDark: !isDark },
      })
    )
  }
}

// Initialize dark mode on page load
;(function () {
  const isDark =
    localStorage.getItem("darkMode") === "true" ||
    (!localStorage.getItem("darkMode") && window.matchMedia("(prefers-color-scheme: dark)").matches)

  if (isDark) {
    document.documentElement.classList.add("dark")
  }
})()

// Utility functions
window.utils = {
  // Copy text to clipboard
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text)
      this.showNotification("Copied to clipboard!", "success")
    } catch (err) {
      console.error("Failed to copy text: ", err)
      this.showNotification("Failed to copy text", "error")
    }
  },

  // Show notification
  showNotification(message, type = "info") {
    const notification = document.createElement("div")
    notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 ${
      type === "success"
        ? "bg-green-500 text-white"
        : type === "error"
          ? "bg-red-500 text-white"
          : type === "warning"
            ? "bg-yellow-500 text-white"
            : "bg-blue-500 text-white"
    }`
    notification.textContent = message

    document.body.appendChild(notification)

    // Fade in
    notification.style.opacity = "0"
    notification.style.transform = "translateX(100%)"
    setTimeout(() => {
      notification.style.transition = "all 0.3s ease"
      notification.style.opacity = "1"
      notification.style.transform = "translateX(0)"
    }, 10)

    // Remove after 3 seconds
    setTimeout(() => {
      notification.style.opacity = "0"
      notification.style.transform = "translateX(100%)"
      setTimeout(() => {
        document.body.removeChild(notification)
      }, 300)
    }, 3000)
  },

  // Debounce function
  debounce(func, wait) {
    let timeout
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout)
        func(...args)
      }
      clearTimeout(timeout)
      timeout = setTimeout(later, wait)
    }
  },
}

// Global functions for finding model components
window.downloadJSON = function (jsonData, filename) {
  const dataStr = typeof jsonData === "string" ? jsonData : JSON.stringify(jsonData, null, 2)
  const dataUri = "data:application/json;charset=utf-8," + encodeURIComponent(dataStr)

  const linkElement = document.createElement("a")
  linkElement.setAttribute("href", dataUri)
  linkElement.setAttribute("download", filename)
  linkElement.click()
}

window.copyToClipboard = function (jsonData) {
  const dataStr = typeof jsonData === "string" ? jsonData : JSON.stringify(jsonData, null, 2)

  navigator.clipboard
    .writeText(dataStr)
    .then(() => {
      showToast("JSON copied to clipboard!")
    })
    .catch(() => {
      showToast("Failed to copy to clipboard")
    })
}

window.showToast = function (message) {
  const toast = document.createElement("div")
  toast.className = "fixed bottom-4 right-4 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg z-50"
  toast.textContent = message
  document.body.appendChild(toast)

  setTimeout(() => {
    toast.remove()
  }, 3000)
}

// HTMX Configuration
htmx.config.globalViewTransitions = false // Disable to prevent history interference
htmx.config.scrollBehavior = 'auto'       // Auto-scroll behavior
htmx.config.includeIndicatorStyles = true // Enable HTMX indicator system
htmx.config.withCredentials = true        // Include cookies in all requests
htmx.config.refreshOnHistoryMiss = false  // Don't refresh page on history miss
htmx.config.historyEnabled = true         // Enable HTMX history management

// Fix breadcrumb and title updates on history navigation
document.addEventListener("htmx:historyRestore", function(event) {
  // Update breadcrumb and title based on restored content
  const mainContent = document.getElementById("main-content")
  const breadcrumbContainer = document.getElementById("breadcrumb-container")

  if (mainContent && breadcrumbContainer) {
    // Check if we're on a detail page (has finding model name in content)
    const modelTitle = mainContent.querySelector("h1, h2")

    if (modelTitle && modelTitle.textContent.trim() !== "Finding Models") {
      // Detail page - use detail breadcrumb and title templates
      const detailBreadcrumbTemplate = document.getElementById("detail-breadcrumb-template")
      const detailTitleTemplate = document.getElementById("detail-title-template")

      if (detailBreadcrumbTemplate && detailTitleTemplate) {
        const modelName = modelTitle.textContent.trim()

        // Update breadcrumb
        const breadcrumbContent = detailBreadcrumbTemplate.content.cloneNode(true)

        // Replace placeholder with actual model name in breadcrumb
        const walker = document.createTreeWalker(
          breadcrumbContent,
          NodeFilter.SHOW_TEXT,
          null,
          false
        )
        let node
        while (node = walker.nextNode()) {
          if (node.textContent.includes('PLACEHOLDER_MODEL_NAME')) {
            node.textContent = modelName
            break
          }
        }

        breadcrumbContainer.innerHTML = ''
        breadcrumbContainer.appendChild(breadcrumbContent)

        // Update title
        const titleContent = detailTitleTemplate.content.cloneNode(true)
        const titleElement = titleContent.querySelector('title')
        if (titleElement) {
          titleElement.textContent = titleElement.textContent.replace('PLACEHOLDER_MODEL_NAME', modelName)
          document.title = titleElement.textContent
        }
      }
    } else {
      // List page - use list breadcrumb and title templates
      const listBreadcrumbTemplate = document.getElementById("list-breadcrumb-template")
      const listTitleTemplate = document.getElementById("list-title-template")

      if (listBreadcrumbTemplate && listTitleTemplate) {
        // Update breadcrumb
        const breadcrumbContent = listBreadcrumbTemplate.content.cloneNode(true)
        breadcrumbContainer.innerHTML = ''
        breadcrumbContainer.appendChild(breadcrumbContent)

        // Update title
        const titleContent = listTitleTemplate.content.cloneNode(true)
        const titleElement = titleContent.querySelector('title')
        if (titleElement) {
          document.title = titleElement.textContent
        }
      }
    }
  }
})

// Smart Flowbite + HTMX Integration with duplicate prevention
let flowbiteInitialized = false

htmx.onLoad(function(content) {
  // Only initialize Flowbite if it hasn't been initialized yet
  if (!flowbiteInitialized) {
    console.log('Initializing Flowbite for the first time')
    initFlowbite()
    flowbiteInitialized = true
  } else {
    // For subsequent loads, only initialize if we have new interactive components
    const flowbiteElements = content?.querySelectorAll ?
      content.querySelectorAll('[data-modal-target], [data-dropdown-target], [data-collapse-target], [data-accordion]') :
      []

    if (flowbiteElements && flowbiteElements.length > 0) {
      console.log('Found new interactive components, reinitializing Flowbite')
      initFlowbite()
    } else {
      console.log('No new interactive components found, skipping Flowbite initialization')
    }
  }

  // Process new content with Alpine.js
  if (window.Alpine && content) {
    try {
      Alpine.initTree(content)
    } catch (error) {
      console.warn('Error initializing Alpine.js after HTMX load:', error)
    }
  }
})




// Initialize Alpine
Alpine.start()

// Initialize Flowbite components on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  initFlowbite()
})

// Console welcome message
console.log("%cWelcome to Finding Model Forge! ⚒︎", "color: #3b82f6; font-size: 16px; font-weight: bold;")

// For any modules that need these
export { Alpine, initFlowbite, htmx }
