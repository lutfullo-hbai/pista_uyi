const tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
  tg.ready();
}

const API_BASE = "";

let categories = [];
let allProducts = [];
let cart = [];
let activeCategory = "all";

async function fetchAPI(url) {
  const res = await fetch(API_BASE + url);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

async function loadCatalog() {
  [categories, allProducts] = await Promise.all([
    fetchAPI("/api/categories"),
    fetchAPI("/api/products"),
  ]);
  renderCategories();
  renderProducts();
}

function renderCategories() {
  const container = document.getElementById("categories");
  container.innerHTML = `<button class="category-btn ${activeCategory === "all" ? "active" : ""}" data-id="all">Hammasi</button>`;
  for (const cat of categories) {
    container.innerHTML += `<button class="category-btn ${activeCategory === String(cat.id) ? "active" : ""}" data-id="${cat.id}">${cat.name}</button>`;
  }
  container.querySelectorAll(".category-btn").forEach((btn) => {
    btn.onclick = () => {
      activeCategory = btn.dataset.id;
      container.querySelectorAll(".category-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("search-input").value = "";
      renderProducts();
    };
  });
}

function getFilteredProducts() {
  let list = allProducts;
  const q = document.getElementById("search-input").value.trim().toLowerCase();
  if (q) {
    list = list.filter((p) =>
      p.name.toLowerCase().includes(q) ||
      (p.description && p.description.toLowerCase().includes(q))
    );
  }
  if (activeCategory && activeCategory !== "all") {
    list = list.filter((p) => p.category_id === parseInt(activeCategory));
  }
  return list;
}

function onSearch() {
  activeCategory = "all";
  document.querySelectorAll(".category-btn").forEach((b) => b.classList.remove("active"));
  const allBtn = document.querySelector('.category-btn[data-id="all"]');
  if (allBtn) allBtn.classList.add("active");
  renderProducts();
}

function renderProducts() {
  const container = document.getElementById("products");
  const filtered = getFilteredProducts();
  if (filtered.length === 0) {
    container.innerHTML = '<p style="grid-column:1/-1;text-align:center;color:var(--hint);padding:40px 0;">Mahsulotlar mavjud emas</p>';
    return;
  }
  container.innerHTML = filtered
    .map(
      (p) => `
      <div class="product-card">
        ${p.image_url ? `<img class="product-image" src="${p.image_url}" alt="${p.name}" loading="lazy">` : `<div class="product-image no-image">📦</div>`}
        <div class="product-name">${p.name}</div>
        ${p.description ? `<div class="product-desc">${p.description}</div>` : ""}
        <div class="product-footer">
          <span class="product-price">${Number(p.price).toLocaleString()} so'm</span>
          <button class="add-btn" onclick="addToCart(${p.id}, '${p.name.replace(/'/g, "\\'")}', ${p.price})">+ Qo'shish</button>
        </div>
      </div>
    `
    )
    .join("");
}

function addToCart(productId, name, price) {
  const existing = cart.find((item) => item.product_id === productId);
  if (existing) {
    existing.quantity++;
  } else {
    cart.push({ product_id: productId, name, price, quantity: 1 });
  }
  updateCartUI();
  tg?.HapticFeedback?.impactOccurred("light");
}

function updateCartUI() {
  const count = cart.reduce((s, i) => s + i.quantity, 0);
  const total = cart.reduce((s, i) => s + i.price * i.quantity, 0);
  const bar = document.getElementById("cart-bar");
  if (count === 0) {
    bar.style.display = "none";
  } else {
    bar.style.display = "flex";
    document.getElementById("cart-info").textContent = `Savat: ${count} ta (${total.toLocaleString()} so'm)`;
  }
  renderCartItems();
}

function renderCartItems() {
  const container = document.getElementById("cart-items");
  if (cart.length === 0) {
    container.innerHTML = '<p style="text-align:center;color:var(--hint);padding:40px 0;">Savat bo\'sh</p>';
    document.getElementById("cart-total").textContent = "";
    return;
  }
  container.innerHTML = cart
    .map(
      (item, idx) => `
      <div class="cart-item">
        <div class="cart-item-info">
          <div class="cart-item-name">${item.name}</div>
          <div class="cart-item-price">${Number(item.price).toLocaleString()} so'm</div>
        </div>
        <div class="cart-item-qty">
          <button class="qty-btn" onclick="changeQty(${idx}, -1)">−</button>
          <span class="qty-value">${item.quantity}</span>
          <button class="qty-btn" onclick="changeQty(${idx}, 1)">+</button>
        </div>
        <button class="delete-btn" onclick="removeItem(${idx})">×</button>
      </div>
    `
    )
    .join("");
  const total = cart.reduce((s, i) => s + i.price * i.quantity, 0);
  document.getElementById("cart-total").textContent = `Jami: ${total.toLocaleString()} so'm`;
}

function changeQty(idx, delta) {
  cart[idx].quantity += delta;
  if (cart[idx].quantity <= 0) {
    cart.splice(idx, 1);
  }
  updateCartUI();
}

function removeItem(idx) {
  cart.splice(idx, 1);
  updateCartUI();
}

function showCatalog() {
  hideAll();
  document.getElementById("catalog-page").style.display = "block";
  document.getElementById("cart-bar").style.display = cart.length > 0 ? "flex" : "none";
}

function showCart() {
  hideAll();
  document.getElementById("cart-page").style.display = "block";
  document.getElementById("cart-bar").style.display = "none";
}

function showOrderForm() {
  if (cart.length === 0) return;
  const user = tg?.initDataUnsafe?.user;
  if (user?.first_name) {
    document.getElementById("name-input").value = user.first_name + (user.last_name ? " " + user.last_name : "");
  }
  hideAll();
  document.getElementById("order-form").style.display = "block";
}

function hideAll() {
  ["catalog-page", "cart-page", "order-form", "success-page", "orders-page"].forEach((id) => {
    document.getElementById(id).style.display = "none";
  });
  document.getElementById("cart-bar").style.display = "none";
}

async function submitOrder() {
  const name = document.getElementById("name-input").value.trim();
  const phone = document.getElementById("phone-input").value.trim();
  const address = document.getElementById("address-input").value.trim();

  if (!name || !phone || !address) {
    tg?.showAlert("Iltimos, barcha maydonlarni to'ldiring!");
    return;
  }

  const user = tg?.initDataUnsafe?.user;
  const payload = {
    user_id: user?.id || 0,
    user_name: name,
    phone,
    address,
    items: cart.map((item) => ({
      product_id: item.product_id,
      name: item.name,
      quantity: item.quantity,
      price: item.price,
    })),
  };

  try {
    const res = await fetch(API_BASE + "/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.order_id) {
      cart = [];
      updateCartUI();
      hideAll();
      document.getElementById("success-page").style.display = "block";
      document.getElementById("success-order-id").textContent = `Buyurtma raqami: #${data.order_id}`;
      tg?.HapticFeedback?.notificationOccurred("success");
    }
  } catch (e) {
    tg?.showAlert("Xatolik yuz berdi. Qayta urinib ko'ring.");
  }
}

function resetAndCatalog() {
  document.getElementById("name-input").value = "";
  document.getElementById("phone-input").value = "";
  document.getElementById("address-input").value = "";
  showCatalog();
}

// ── Orders History ──

async function showOrders() {
  const user = tg?.initDataUnsafe?.user;
  if (!user?.id) {
    tg?.showAlert("Foydalanuvchi ma'lumotlari topilmadi.");
    return;
  }
  hideAll();
  document.getElementById("orders-page").style.display = "block";
  const container = document.getElementById("orders-list");
  container.innerHTML = '<p style="text-align:center;color:var(--hint);padding:40px 0;">Yuklanmoqda...</p>';
  try {
    const orders = await fetchAPI(`/api/orders/user/${user.id}`);
    if (orders.length === 0) {
      container.innerHTML = '<p style="text-align:center;color:var(--hint);padding:40px 0;">Sizning buyurtmalaringiz yo\'q</p>';
      return;
    }
    container.innerHTML = orders
      .map(
        (o) => `
        <div class="order-card">
          <div class="order-id">Buyurtma #${o.id}</div>
          <div class="order-status status-${o.status}">${getStatusText(o.status)}</div>
          <div class="order-detail">💰 ${Number(o.total_amount).toLocaleString()} so'm</div>
          <div class="order-detail">📍 ${o.address}</div>
          <div class="order-detail">📅 ${o.created_at ? new Date(o.created_at).toLocaleDateString("uz-UZ") : "—"}</div>
        </div>
      `
      )
      .join("");
  } catch (e) {
    container.innerHTML = '<p style="text-align:center;color:red;padding:40px 0;">Xatolik yuz berdi</p>';
  }
}

function getStatusText(status) {
  const map = {
    pending: "⏳ Kutilmoqda",
    processing: "👨‍🍳 Tayyorlanmoqda",
    delivered: "✅ Yetkazilgan",
    cancelled: "❌ Bekor qilingan",
  };
  return map[status] || status;
}

loadCatalog();
