const fileInput = document.getElementById('image_file')
const previewImg = document.getElementById('previev-img')
const previewContainer = document.getElementById('preview-section')

fileInput.addEventListener('change', ()=>{
    const file = fileInput.files[0];
    if (file){
        const tempUrl= URL.createObjectURL(file);
        previewImg.src= tempUrl;
        previewImg.style.display = "block";
    }
});
const form = document.getElementById('add-item-form')

form.addEventListener('submit', async (event) =>{
    event.preventDefault();
    const formData = new FormData();
    formData.append("name", document.getElementById('name').value);
    formData.append("storage_sector", document.getElementById('sector').value);
    formData.append("weight", document.getElementById('weight').value);
    formData.append("quantity", document.getElementById('quantity').value);
    formData.append("is_dangerous", document.getElementById('is_dangerous').checked);
    formData.append("image_file", fileInput.files[0]);

    const response = await fetch("/items", {
        method: "POST",
        body: formData
    });
    if (response.status ===201){
        alert("Все топчик")
        window.location.href = "/"
    }else{
        alert("ох я сплоховал")
        console.log(await response.json)
    }
})