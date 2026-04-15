// FeedOptima Frontend JavaScript

const API_BASE = 'http://localhost:8000'; // Backend API URL

// DOM Elements
const rationForm = document.getElementById('rationForm');
const resultsSection = document.getElementById('results');
const rationResults = document.getElementById('rationResults');
const aiExplanation = document.getElementById('aiExplanation');
const loadCatalogBtn = document.getElementById('loadCatalog');
const catalogResults = document.getElementById('catalogResults');

// Form submission handler
rationForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get form data
    const formData = new FormData(rationForm);
    const requestData = {
        animal_type: formData.get('animalType'),
        weight_kg: parseFloat(formData.get('weight')),
        milk_production_liters: parseFloat(formData.get('milkProduction')) || 0,
        pregnancy_stage: formData.get('pregnancyStage'),
        lactation_stage: formData.get('lactationStage'),
        max_feed_cost_per_day: parseFloat(formData.get('feedCost')),
        include_ai_explanation: document.getElementById('includeAI').checked
    };

    // Show loading
    rationResults.innerHTML = '<div class="loading">Optimizing ration...</div>';
    resultsSection.style.display = 'block';
    aiExplanation.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/ration/optimize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayRationResults(data);

    } catch (error) {
        console.error('Error:', error);
        rationResults.innerHTML = `<div class="error">Error optimizing ration: ${error.message}. Make sure the backend is running on ${API_BASE}</div>`;
    }
});

// Load catalog handler
loadCatalogBtn.addEventListener('click', async () => {
    catalogResults.innerHTML = '<div class="loading">Loading feed catalog...</div>';

    try {
        const response = await fetch(`${API_BASE}/catalog`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayCatalog(data);

    } catch (error) {
        console.error('Error:', error);
        catalogResults.innerHTML = `<div class="error">Error loading catalog: ${error.message}. Make sure the backend is running on ${API_BASE}</div>`;
    }
});

// Display ration results
function displayRationResults(data) {
    let html = '<h3>Recommended Feed Components:</h3>';

    data.components.forEach(component => {
        html += `
            <div class="ration-item">
                <h4>${component.feed_name}</h4>
                <p><strong>Quantity:</strong> ${component.quantity_kg.toFixed(2)} kg</p>
                <p><strong>Cost:</strong> ₹${component.cost_per_day.toFixed(2)}</p>
                <p><strong>Nutrients:</strong> CP: ${component.crude_protein}%, TDN: ${component.tdn}%</p>
            </div>
        `;
    });

    html += `<div class="total-cost">Total Daily Cost: ₹${data.total_cost_per_day.toFixed(2)}</div>`;

    if (data.instructions) {
        html += `<div class="ration-item"><h4>Feeding Instructions:</h4><p>${data.instructions}</p></div>`;
    }

    rationResults.innerHTML = html;

    // Show AI explanation if available
    if (data.ai_explanation) {
        aiExplanation.innerHTML = `<h4>AI Explanation:</h4><p>${data.ai_explanation}</p>`;
        aiExplanation.style.display = 'block';
    }
}

// Display catalog
function displayCatalog(data) {
    if (!data.ingredients || data.ingredients.length === 0) {
        catalogResults.innerHTML = '<p>No ingredients found in catalog.</p>';
        return;
    }

    let html = `<p>Found ${data.ingredients.length} feed ingredients:</p>`;

    data.ingredients.forEach(ingredient => {
        html += `
            <div class="catalog-item">
                <strong>${ingredient.name}</strong> - ₹${ingredient.price_per_kg}/kg
                (CP: ${ingredient.crude_protein}%, TDN: ${ingredient.tdn}%)
            </div>
        `;
    });

    catalogResults.innerHTML = html;
}

// Initialize - try to load catalog on page load
document.addEventListener('DOMContentLoaded', () => {
    // Optional: Auto-load catalog on page load
    // loadCatalogBtn.click();
});