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
        species: formData.get('animalType'),
        body_weight_kg: parseFloat(formData.get('weight')),
        milk_yield_lpd: parseFloat(formData.get('milkProduction')) || 0,
        purpose: formData.get('purpose'),
        use_ai: document.getElementById('includeAI').checked,
        max_cost_per_day: parseFloat(formData.get('maxCost')) || null,
        preferred_feeds: formData.get('preferredFeeds') ? formData.get('preferredFeeds').split(',').map(s => s.trim()).filter(s => s) : [],
        avoid_feeds: formData.get('avoidFeeds') ? formData.get('avoidFeeds').split(',').map(s => s.trim()).filter(s => s) : [],
        region: 'general'  // Could be made configurable later
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
                <h4>${component.name} (${component.category})</h4>
                <p><strong>Quantity:</strong> ${component.weight_kg.toFixed(2)} kg</p>
                <p><strong>Dry Matter:</strong> ${component.dry_matter_kg.toFixed(2)} kg</p>
                <p><strong>Crude Protein:</strong> ${component.crude_protein_pct.toFixed(1)}%</p>
                <p><strong>Energy:</strong> ${component.energy_mj.toFixed(1)} MJ</p>
                <p><strong>Minerals:</strong> Ca: ${(component.calcium_pct * 100).toFixed(2)}%, P: ${(component.phosphorus_pct * 100).toFixed(2)}%</p>
                <p><strong>Fiber:</strong> ${component.fiber_pct.toFixed(1)}%</p>
                <p><strong>Cost:</strong> ₹${component.cost_inr.toFixed(2)}</p>
                ${component.availability_score < 1 ? `<p><em>Availability: ${(component.availability_score * 100).toFixed(0)}%</em></p>` : ''}
            </div>
        `;
    });

    html += `<div class="total-cost">Total Dry Matter: ${data.total_dry_matter_kg.toFixed(2)} kg | Total Daily Cost: ₹${data.total_cost_inr.toFixed(2)}</div>`;

    if (data.summary) {
        html += `<div class="ration-item"><h4>Summary:</h4><p>${data.summary}</p></div>`;
    }

    if (data.instructions && data.instructions.length > 0) {
        html += `<div class="ration-item"><h4>Feeding Instructions:</h4><ol>`;
        data.instructions.forEach(instruction => {
            html += `<li>${instruction}</li>`;
        });
        html += `</ol></div>`;
    }

    rationResults.innerHTML = html;

    // Show AI explanation if available
    if (data.ai_notes) {
        aiExplanation.innerHTML = `<h4>AI Explanation:</h4><p>${data.ai_notes}</p>`;
        aiExplanation.style.display = 'block';
    }
}

// Display catalog
function displayCatalog(data) {
    if (!data || data.length === 0) {
        catalogResults.innerHTML = '<p>No ingredients found in catalog.</p>';
        return;
    }

    let html = `<p>Found ${data.length} feed ingredients:</p>`;

    data.forEach(ingredient => {
        const price = ingredient.latest_price_per_kg ? `₹${ingredient.latest_price_per_kg.toFixed(2)}/kg` : 'Price not set';
        html += `
            <div class="catalog-item">
                <strong>${ingredient.name}</strong> (${ingredient.category}) - ${price}
                <br>DM: ${ingredient.dry_matter_pct.toFixed(1)}%, CP: ${ingredient.crude_protein_pct.toFixed(1)}%, Energy: ${ingredient.energy_mj_per_kg.toFixed(1)} MJ/kg
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