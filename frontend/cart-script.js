const userId = localStorage.getItem('warehouse_user_id')
const container = document.getElementById('cart-container')
const emptyMsg = document.getElementById('empty-msg')

async function loadCart() {
    if (!userId) return
    const API_URL = `/cart?user_id=${userId}`
    try{
        const response = await fetch(API_URL)
        const cardData = await response.json()
        
        if(Object.keys(cardData).length === 0){
            emptyMsg.style.display = 'block'
            container.innerHTML = '' // очищаем контейнер
            return
        }
        
        emptyMsg.style.display = 'none' // скрываем сообщение, если есть товары
        await renderCart(cardData) 
        
    } catch(error){
        console.error("Ошибка при загрузке с сервера:", error)
        emptyMsg.style.display = 'block'
        emptyMsg.textContent = 'Ошибка загрузки корзины'
    }
}

async function renderCart(cardData) {
    container.innerHTML = ""
    for (const itemId in cardData){
        const entry = cardData[itemId]
        const quantity = entry.quantity
        const item = entry.item
        if (!item) continue
        const card = document.createElement('div')
        card.className = 'card'
        card.innerHTML = `
            <h3 class="card-title">${item.name}</h3>
            <p>количество в заказе: <b>${quantity} шт.</b></p>
            <p>общий вес: ${(item.weight * quantity).toFixed(2)} кг</p>
        `
        container.appendChild(card)
    }
}

loadCart();