/* export.js — PNG, SVG, and PDF export functions */

'use strict';

/**
 * Initialize export buttons.
 * @param {Object} cy - Cytoscape instance
 * @param {string} divisionName - Division name for file naming
 */
function initExport(cy, divisionName) {
  const safeName = (divisionName || 'tournament').replace(/[^a-z0-9]/gi, '_');

  document.getElementById('export-png').addEventListener('click', () => {
    exportPNG(cy, safeName);
  });

  document.getElementById('export-svg').addEventListener('click', () => {
    exportSVG(cy, safeName);
  });

  document.getElementById('export-pdf').addEventListener('click', () => {
    exportPDF(cy, safeName);
  });
}

/**
 * Export graph as PNG image.
 *
 * NOTE: cy.png() / cy.svg() capture only the Cytoscape canvas layer.
 * The HTML overlay layer rendered by cytoscape-node-html-label (.match-card,
 * .ranking-card elements) is NOT captured — exports show invisible match nodes
 * without team name text. This is a known limitation of the HTML overlay approach.
 */
function exportPNG(cy, name) {
  const png = cy.png({ full: true, scale: 2, bg: '#ffffff' });
  const link = document.createElement('a');
  link.href = png;
  link.download = `${name}_sorting_network.png`;
  // Must be in the DOM for Firefox to honor programmatic click
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Export graph as SVG vector image.
 */
function exportSVG(cy, name) {
  const svg = cy.svg({ full: true, scale: 1, bg: '#ffffff' });
  const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${name}_sorting_network.svg`;
  // Must be in the DOM for Firefox to honor programmatic click
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * Export graph as PDF via jsPDF.
 * Falls back to SVG download if jsPDF is unavailable.
 */
async function exportPDF(cy, name) {
  const svg = cy.svg({ full: true, scale: 1, bg: '#ffffff' });

  if (typeof window.jspdf === 'undefined') {
    // Fallback: just download SVG
    console.warn('jsPDF not available, falling back to SVG export');
    exportSVG(cy, name);
    return;
  }

  try {
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(svg, 'image/svg+xml');
    const svgEl = svgDoc.documentElement;

    const w = parseFloat(svgEl.getAttribute('width') || 800);
    const h = parseFloat(svgEl.getAttribute('height') || 600);

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({
      orientation: w > h ? 'landscape' : 'portrait',
      unit: 'px',
      format: [w, h],
    });

    // Use svg2pdf if available
    if (typeof svg2pdf !== 'undefined') {
      await svg2pdf(svgEl, doc, { x: 0, y: 0, width: w, height: h });
    } else {
      // Fallback: embed SVG as image
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();
      const url = 'data:image/svg+xml,' + encodeURIComponent(svg);
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = url;
      });
      canvas.width = w * 2;
      canvas.height = h * 2;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      doc.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, w, h);
    }

    doc.save(`${name}_sorting_network.pdf`);
  } catch (err) {
    console.error('PDF export failed:', err);
    exportSVG(cy, name);
  }
}
