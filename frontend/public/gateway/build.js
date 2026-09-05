const fs = require('fs');

const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ShopEase - Oversized Layered T-Shirt</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#f8f9fa;--text:#111827;--muted:#6b7280;--border:#e5e7eb;
      --primary:#000000;--primary-hover:#333333;--green:#10b981;--red:#ef4444;--yellow:#f59e0b;
    }
    body{font-family:'Inter',sans-serif;color:var(--text);background-color:#ffffff;}
    
    /* Fake E-commerce Page Background */
    .store-nav { padding: 16px 40px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
    .store-brand { font-size: 24px; font-weight: 800; letter-spacing: -1px; }
    .store-links { display: flex; gap: 24px; font-size: 14px; font-weight: 500; }
    .store-icons { font-size: 20px; }
    
    .product-page { max-width: 1200px; margin: 0 auto; padding: 40px; display: grid; grid-template-columns: 1fr 1fr; gap: 60px; }
    .product-image { background: #f3f4f6; border-radius: 8px; aspect-ratio: 4/5; display: flex; align-items: center; justify-content: center; font-size: 80px; color: #d1d5db; }
    .product-details { padding-top: 20px; }
    .product-title { font-size: 28px; font-weight: 700; margin-bottom: 12px; line-height: 1.2; }
    .product-price { font-size: 24px; font-weight: 600; margin-bottom: 24px; }
    .product-discount { color: var(--green); font-size: 14px; font-weight: 700; background: #ecfdf5; padding: 4px 8px; border-radius: 4px; margin-left: 12px; vertical-align: middle; }
    .product-options { margin-bottom: 32px; }
    .option-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
    .size-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    .size-btn { padding: 12px; border: 1px solid var(--border); border-radius: 4px; background: white; cursor: pointer; font-weight: 500; }
    .size-btn.active { border-color: var(--primary); border-width: 2px; }
    
    .buy-actions { display: flex; gap: 16px; margin-bottom: 40px; }
    .add-cart-btn { flex: 1; padding: 16px; border: 1px solid var(--primary); background: white; color: var(--primary); font-weight: 700; border-radius: 4px; cursor: pointer; }
    .buy-now-btn { flex: 1; padding: 16px; background: var(--primary); color: white; font-weight: 700; border-radius: 4px; cursor: pointer; transition: background 0.2s; }
    .buy-now-btn:hover { background: var(--primary-hover); }

    .test-panel { margin-top: 40px; padding: 20px; border: 1px dashed #ccc; border-radius: 8px; background: #fafafa; }
    
    /* ---------------------------------------------------- */
    /* Checkout Modal (The Gateway)                         */
    /* ---------------------------------------------------- */
    
    /* Overlay backdrop */
    .modal-overlay {
      position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px);
      display: none; justify-content: center; align-items: center; z-index: 1000;
    }
    .modal-overlay.active { display: flex; }
    
    /* The popup container */
    .checkout-modal {
      width: 100%; max-width: 440px; background: #ffffff; border-radius: 12px;
      max-height: 90vh; display: flex; flex-direction: column; overflow: hidden;
      box-shadow: 0 20px 40px rgba(0,0,0,0.2); animation: slideUp 0.3s ease-out;
    }
    @keyframes slideUp {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
    
    /* Checkout Header */
    .co-header {
      display: flex; justify-content: space-between; align-items: center; padding: 16px 20px;
      border-bottom: 1px solid var(--border); background: white;
    }
    .co-close { cursor: pointer; font-size: 20px; color: var(--muted); padding: 4px; line-height: 1; border: none; background: transparent;}
    .co-brand { font-weight: 800; font-size: 16px; display: flex; align-items: center; gap: 8px;}
    .co-secure { font-size: 11px; color: var(--muted); display: flex; align-items: center; gap: 4px;}
    .co-banner { background: var(--primary); color: white; text-align: center; font-size: 11px; font-weight: 600; padding: 6px; }

    /* Content Area */
    .co-content { padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; background: #f9fafb; flex: 1; }

    /* Shared Card Styles */
    .c-card { border: 1px solid var(--border); border-radius: 12px; padding: 16px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.02);}
    .c-title { font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
    
    /* Summary inside Modal */
    .o-sum { display: flex; justify-content: space-between; align-items: center; }
    .o-icon { font-size: 24px; color: var(--muted); }
    .o-det { flex: 1; margin-left: 12px; }
    .o-name { font-weight: 600; font-size: 14px; }
    .o-save { font-size: 11px; color: var(--green); background: #ecfdf5; padding: 2px 6px; border-radius: 10px; display: inline-block; margin-top: 4px; }
    .o-prc { text-align: right; }
    .o-fin { font-weight: 700; font-size: 16px; display:flex; align-items:center; gap:2px; justify-content:flex-end;}
    .amt-edit { width: 60px; border: 1px solid #ccc; border-radius: 4px; padding: 2px 4px; text-align: right; font-weight: 700; font-size: 16px; outline:none; }

    /* Inputs */
    .ig { position: relative; margin-top: 12px; margin-bottom: 8px;}
    .ilbl { position: absolute; top: -8px; left: 12px; background: white; padding: 0 4px; font-size: 11px; color: var(--muted); }
    .iinp { width: 100%; padding: 12px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; outline: none; transition: border 0.2s; background: white; }
    .iinp:focus { border-color: var(--primary); }

    /* Payment Methods Accordion */
    .pm-item { border: 1px solid var(--border); border-radius: 12px; overflow: hidden; background: white; margin-bottom: 12px; }
    .pm-hdr { padding: 16px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
    .pm-hdr:hover { background: #fafafa; }
    .pm-item.active .pm-hdr { background: #f0fdf4; border-bottom: 1px solid var(--border); }
    .pm-l { display: flex; align-items: center; gap: 12px; font-weight: 600; font-size: 14px; }
    .pm-ico { font-size: 20px; width: 24px; text-align: center; }
    .pm-r { text-align: right; }
    .pm-tag { font-size: 10px; background: var(--green); color: white; padding: 2px 6px; border-radius: 4px; margin-bottom: 4px; display: inline-block;}
    .pm-prc { font-weight: 700; font-size: 14px; }
    
    .pm-body { padding: 16px; display: none; background: white; }
    .pm-item.active .pm-body { display: block; }
    
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

    /* Bottom Actions */
    .co-footer { padding: 16px; border-top: 1px solid var(--border); background: white; }
    .trust { display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 11px; color: var(--muted); margin-bottom: 12px; }
    .c-btn { width: 100%; padding: 14px; background: var(--primary); color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; transition: opacity 0.2s; }
    .c-btn:active { opacity: 0.8; }
    
    /* Result / Loading States inside Modal */
    .co-status { position: absolute; inset: 0; background: rgba(255,255,255,0.95); z-index: 10; display: none; flex-direction: column; align-items: center; justify-content: center; padding: 24px; text-align: center; }
    .co-status.active { display: flex; }
    
    .spinner { width: 40px; height: 40px; border: 3px solid #f3f3f3; border-top: 3px solid var(--primary); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 20px; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    
    .r-icon { width: 64px; height: 64px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; margin-bottom: 16px; }
    .r-ttl { font-size: 20px; font-weight: 800; margin-bottom: 8px; }
    .r-sub { font-size: 13px; color: var(--muted); margin-bottom: 20px; }
    .r-box { background: white; border: 1px solid var(--border); border-radius: 12px; padding: 16px; width: 100%; margin-bottom: 20px; text-align: left; }
    .r-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }
    .r-lbl { color: var(--muted); }
    .r-val { font-weight: 600; }
    
    .sigs-box { margin-top: 12px; border-top: 1px solid var(--border); padding-top: 12px; }
    .sig-row { font-size: 11px; margin-bottom: 6px; display: flex; align-items: flex-start; gap: 6px; }
    .sig-dot { width: 6px; height: 6px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
    
    /* Steps */
    .step { display: none; }
    .step.active { display: block; }
  </style>
</head>
<body>

<!-- Fake Background Page -->
<nav class="store-nav">
  <div class="store-brand">UrbanWear</div>
  <div class="store-links">
    <span>Home</span><span>T-shirts</span><span>Hoodies</span><span>SALE</span>
  </div>
  <div class="store-icons">🔍 🛍️</div>
</nav>

<div class="product-page">
  <div class="product-image">
    👕
  </div>
  <div class="product-details">
    <h1 class="product-title">Brown & Cream "00" Oversized Layered T-Shirt</h1>
    <div class="product-price">
      ₹799 <span style="text-decoration:line-through; color:var(--muted); font-size: 16px; font-weight: 400; margin-left: 8px;">₹1,499</span>
      <span class="product-discount">50% OFF</span>
    </div>
    
    <div class="product-options">
      <div class="option-title">Select Size</div>
      <div class="size-grid">
        <button class="size-btn">M</button>
        <button class="size-btn">L</button>
        <button class="size-btn active">XL</button>
        <button class="size-btn">XXL</button>
      </div>
      <div style="font-size: 12px; color: var(--red); margin-top: 8px;">Only 2 items left in XL</div>
    </div>
    
    <div class="buy-actions">
      <button class="add-cart-btn">ADD TO CART</button>
      <button class="buy-now-btn" onclick="openCheckout()">BUY IT NOW</button>
    </div>
    
    <div class="test-panel">
      <h3 style="margin-bottom: 8px; font-size: 14px;">Demo Settings (RiskShield)</h3>
      <p style="font-size: 12px; color: #666; margin-bottom: 12px;">Change the test scenario before opening the checkout modal.</p>
      <select id="scenarioSelect" style="width: 100%; padding: 8px; margin-bottom: 8px;" onchange="updateScenario()">
        <option value="normal">Normal Purchase (₹799, India)</option>
        <option value="high">High Value Electronics (₹84,999, India)</option>
        <option value="foreign">Suspicious Foreign IP (₹1, Russia)</option>
        <option value="micro">Card Verify Probe (₹0.01, Nigeria)</option>
      </select>
    </div>
  </div>
</div>

<!-- ========================================== -->
<!-- Checkout Popup Modal                       -->
<!-- ========================================== -->
<div class="modal-overlay" id="checkoutModal">
  <div class="checkout-modal">
    
    <div class="co-header">
      <button class="co-close" onclick="closeCheckout()">❮</button>
      <div class="co-brand">Blazerpay</div>
      <div class="co-secure">🔒 100% Secured</div>
    </div>
    <div class="co-banner">Extra Discount Available at Payment Step</div>
    
    <div class="co-content" style="position: relative;">
      
      <!-- Step 1: Login / Identity -->
      <div id="step-id" class="step active">
        
        <div class="c-card" style="margin-bottom: 16px;">
          <div class="o-sum">
            <div class="o-icon">🛒</div>
            <div class="o-det">
              <div class="o-name">Order Summary</div>
              <div class="o-save">₹700 saved so far</div>
            </div>
            <div class="o-prc">
              <div class="o-fin">₹<input type="number" id="amtInput1" class="amt-edit" value="799" /></div>
            </div>
          </div>
        </div>

        <div class="c-card" style="border-top: 3px solid #fde68a;">
          <div class="c-title" style="text-align: center; color: #b45309; font-size: 12px;">Login to continue</div>
          <p style="font-size: 12px; color: var(--muted); text-align: center; margin-bottom: 16px;">Enter mobile number to link past transactions for risk evaluation.</p>
          
          <div class="ig">
            <span class="ilbl">Enter Mobile Number</span>
            <input type="text" id="userId" class="iinp" placeholder="+91 9893484443" value="+91 9893484443" />
          </div>
        </div>
        
      </div>

      <!-- Step 2: Payment Methods -->
      <div id="step-pay" class="step">
        
        <div class="c-title" style="margin-top: 4px;">Delivery Details</div>
        <div class="c-card" style="margin-bottom: 24px;">
          <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">Deliver to <span id="dispUser"></span></div>
          <div style="font-size: 12px; color: var(--muted); line-height: 1.4;">
            Hig N42 B Block, Delivery After 5 PM<br/>
            Kanpur, Uttar Pradesh 208020
          </div>
        </div>

        <div class="c-title">Payment Options</div>
        
        <!-- UPI -->
        <div class="pm-item" id="pm-upi">
          <div class="pm-hdr" onclick="selPM('upi')">
            <div class="pm-l"><div class="pm-ico">📱</div>UPI</div>
            <div class="pm-r">
              <div class="pm-tag">Get 5% off</div>
              <div class="pm-prc">₹<span class="d-amt">759.05</span></div>
            </div>
          </div>
          <div class="pm-body">
            <div style="text-align: center; padding: 10px 0;">
              <div style="width: 120px; height: 120px; background: #eee; margin: 0 auto 12px; display: flex; align-items: center; justify-content: center; border-radius: 8px;">
                <span style="color: var(--muted); font-size: 12px;">[ Fake QR ]</span>
              </div>
              <div class="ig">
                <span class="ilbl">Or enter UPI ID</span>
                <input type="text" id="upiId" class="iinp" placeholder="yourname@upi" />
              </div>
            </div>
          </div>
        </div>

        <!-- Cards -->
        <div class="pm-item active" id="pm-card">
          <div class="pm-hdr" onclick="selPM('card')">
            <div class="pm-l"><div class="pm-ico">💳</div>Debit/Credit Cards</div>
            <div class="pm-r">
              <div class="pm-prc">₹<span class="d-amt">799.00</span></div>
            </div>
          </div>
          <div class="pm-body">
            <div class="ig">
              <span class="ilbl">Card Number</span>
              <input type="text" id="cardNum" class="iinp" placeholder="4111 1111 1111 1111" maxlength="19" />
            </div>
            <div class="ig">
              <span class="ilbl">Name on Card</span>
              <input type="text" id="cardName" class="iinp" placeholder="John Doe" />
            </div>
            <div class="grid2">
              <div class="ig">
                <span class="ilbl">Expiry</span>
                <input type="text" id="cardExp" class="iinp" placeholder="MM/YY" maxlength="5" />
              </div>
              <div class="ig">
                <span class="ilbl">CVV</span>
                <input type="password" id="cardCvv" class="iinp" placeholder="123" maxlength="4" />
              </div>
            </div>
          </div>
        </div>
        
      </div>
      
      <!-- Overlays inside Content Area -->
      <div id="co-loading" class="co-status">
        <div class="spinner"></div>
        <h2 style="font-size: 16px;">Risk Evaluation...</h2>
        <p style="color: var(--muted); font-size: 12px; margin-top: 8px;">Sending details to RiskShield engine</p>
      </div>
      
      <div id="co-result" class="co-status" style="justify-content: flex-start; padding-top: 40px;">
        <div id="rIcon" class="r-icon"></div>
        <div id="rTitle" class="r-ttl"></div>
        <div id="rSub" class="r-sub"></div>
        
        <div class="r-box">
          <div class="r-row"><span class="r-lbl">Amount</span><span class="r-val" id="rAmt"></span></div>
          <div class="r-row"><span class="r-lbl">Risk Level</span><span class="r-val" id="rLvl"></span></div>
          <div class="r-row"><span class="r-lbl">Risk Score</span><span class="r-val" id="rScore"></span></div>
          <div class="r-row" style="margin-top: 6px; font-size: 11px; color: var(--muted);">
            Txn ID: <span id="rTxn"></span>
          </div>
          
          <div id="rSigs" class="sigs-box"></div>
        </div>
        
        <a href="http://localhost:3000/transactions" target="_blank" class="c-btn" style="text-decoration: none; display: block; text-align: center; margin-bottom: 12px;">View in RiskShield Dashboard</a>
        <button class="c-btn" onclick="closeCheckout()" style="background: #f3f4f6; color: var(--primary); border: 1px solid var(--border);">Close</button>
      </div>

    </div>
    
    <!-- Footer actions -->
    <div class="co-footer" id="coFooter">
      <div class="trust">🔒 100% data security and encryption</div>
      <button id="btnContinue" class="c-btn" onclick="goStepPay()">Continue</button>
      <button id="btnPay" class="c-btn" onclick="doPay()" style="display: none;">Pay Now</button>
    </div>
    
  </div>
</div>

<script>
  // -- Test Scenarios --
  const scenarios = {
    'normal':  { amt: 799,   ip: '49.36.100.12',   ctry: 'IN', city: 'Kanpur', lat: 26.449, lon: 80.331 },
    'high':    { amt: 84999, ip: '49.36.100.12',   ctry: 'IN', city: 'Delhi',  lat: 28.613, lon: 77.209 },
    'foreign': { amt: 1,     ip: '185.220.101.45', ctry: 'RU', city: 'Moscow', lat: 55.755, lon: 37.617 },
    'micro':   { amt: 0.01,  ip: '197.210.54.96',  ctry: 'NG', city: 'Lagos',  lat: 6.524,  lon: 3.379 }
  };
  let activeScene = scenarios['normal'];

  function updateScenario() {
    const key = document.getElementById('scenarioSelect').value;
    activeScene = scenarios[key];
    document.getElementById('amtInput1').value = activeScene.amt;
    updateAmts();
  }

  // -- Modal state --
  let finalAmt = 799;
  let pm = 'card';

  function openCheckout() {
    document.getElementById('checkoutModal').classList.add('active');
    updateAmts();
  }
  function closeCheckout() {
    document.getElementById('checkoutModal').classList.remove('active');
    // reset
    document.getElementById('step-pay').classList.remove('active');
    document.getElementById('step-id').classList.add('active');
    document.getElementById('btnPay').style.display = 'none';
    document.getElementById('btnContinue').style.display = 'block';
    document.getElementById('co-loading').classList.remove('active');
    document.getElementById('co-result').classList.remove('active');
    document.getElementById('coFooter').style.display = 'block';
  }

  function updateAmts() {
    finalAmt = parseFloat(document.getElementById('amtInput1').value) || 0;
    document.querySelectorAll('.d-amt').forEach(el => {
      let v = el.closest('#pm-upi') ? (finalAmt * 0.95).toFixed(2) : finalAmt.toFixed(2);
      el.textContent = v;
    });
  }

  document.getElementById('amtInput1').addEventListener('input', updateAmts);

  // Formatting
  document.getElementById('cardNum').addEventListener('input', e => {
    let v = e.target.value.replace(/\\D/g, '').slice(0, 16);
    e.target.value = v.replace(/(.{4})/g, '$1 ').trim();
  });
  document.getElementById('cardExp').addEventListener('input', e => {
    let v = e.target.value.replace(/\\D/g, '').slice(0, 4);
    if(v.length > 2) v = v.slice(0, 2) + '/' + v.slice(2);
    e.target.value = v;
  });

  function selPM(sel) {
    pm = sel;
    document.querySelectorAll('.pm-item').forEach(el => el.classList.remove('active'));
    document.getElementById('pm-' + sel).classList.add('active');
  }

  function goStepPay() {
    const u = document.getElementById('userId').value.trim();
    if (!u) { alert('Enter mobile number'); return; }
    document.getElementById('dispUser').textContent = u;
    
    document.getElementById('step-id').classList.remove('active');
    document.getElementById('step-pay').classList.add('active');
    document.getElementById('btnContinue').style.display = 'none';
    document.getElementById('btnPay').style.display = 'block';
  }

  async function doPay() {
    const payAmt = pm === 'upi' ? finalAmt * 0.95 : finalAmt;
    if (payAmt <= 0) { alert('Invalid amount'); return; }

    document.getElementById('co-loading').classList.add('active');
    document.getElementById('coFooter').style.display = 'none'; // hide footer during loading

    const payload = {
      external_transaction_id: 'txn_' + Math.random().toString(36).slice(2,10),
      amount: parseFloat(payAmt.toFixed(2)),
      currency: 'INR',
      payment_method: pm === 'upi' ? 'upi' : 'credit_card',
      ip_address: activeScene.ip,
      country: activeScene.ctry,
      city: activeScene.city,
      latitude: activeScene.lat,
      longitude: activeScene.lon,
      customer: {
        external_customer_id: document.getElementById('userId').value.trim(),
        status: 'active'
      },
      merchant: {
        external_merchant_id: 'merch_urbanwear',
        category: 'ecommerce',
        status: 'active'
      },
      device: {
        device_fingerprint: 'dev_' + Math.random().toString(36).slice(2,14),
        device_type: 'mobile',
        operating_system: 'Windows'
      }
    };

    try {
      const res = await fetch('https://riskshield-backend-x6h5.onrender.com/payments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if(!res.ok) throw new Error('API Error: ' + res.status);
      const tx = await res.json();
      
      setTimeout(() => showRes(tx), 1200);
    } catch(e) {
      alert('RiskShield connection failed. ' + e.message);
      document.getElementById('co-loading').classList.remove('active');
      document.getElementById('coFooter').style.display = 'block';
    }
  }

  function showRes(tx) {
    document.getElementById('co-loading').classList.remove('active');
    document.getElementById('co-result').classList.add('active');

    const re = tx.risk_evaluation || {};
    const dec = re.decision || 'APPROVE';
    
    const i = document.getElementById('rIcon'), t = document.getElementById('rTitle');
    if (dec === 'APPROVE') {
      i.innerHTML='✓'; i.style.background='#d1fae5'; i.style.color='#10b981';
      t.textContent='Payment Successful'; t.style.color='#10b981';
      document.getElementById('rSub').textContent='Order placed successfully.';
    } else if (dec === 'REVIEW') {
      i.innerHTML='⚠'; i.style.background='#fef3c7'; i.style.color='#f59e0b';
      t.textContent='Under Review'; t.style.color='#f59e0b';
      document.getElementById('rSub').textContent='Flagged for manual review.';
    } else {
      i.innerHTML='✕'; i.style.background='#fee2e2'; i.style.color='#ef4444';
      t.textContent='Payment Blocked'; t.style.color='#ef4444';
      document.getElementById('rSub').textContent='Declined due to high risk.';
    }

    document.getElementById('rAmt').textContent = '₹' + tx.amount;
    document.getElementById('rLvl').textContent = re.risk_level || 'N/A';
    document.getElementById('rScore').textContent = re.score || '0';
    document.getElementById('rTxn').textContent = tx.external_transaction_id;

    const sb = document.getElementById('rSigs');
    if (re.signals && re.signals.length > 0) {
      sb.innerHTML = '<div style="font-size: 10px; color: var(--muted); margin-bottom: 6px;">RISK SIGNALS</div>' + 
        re.signals.map(s => {
          let c = s.severity === 'CRITICAL' || s.severity === 'HIGH' ? '#ef4444' : '#f59e0b';
          return \`<div class="sig-row"><div class="sig-dot" style="background: \${c}"></div><div><strong>\${s.name}</strong><br/><span style="color:var(--muted)">\${s.explanation}</span></div></div>\`;
        }).join('');
    } else {
      sb.innerHTML = '<div style="font-size: 11px; color: var(--green);">No risk signals detected.</div>';
    }
  }
</script>
</body>
</html>`;

fs.writeFileSync('index.html', html, 'utf8');
console.log('Updated index.html to modal layout');
