function uploadImage() {
    const fileInput = document.getElementById('fileUpload');
    const file = fileInput.files[0];

    fetch('/api/upload-url', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({'filename': file.name, 'contentType': file.type})
    })
    .then(res => res.json())
    .then(data => fetch(data.uploadUrl, {method: 'PUT', body: file}))
    .then(() => alert('Upload realizado com sucesso!'))
    .catch(err => alert('Erro no upload: ' + err));
}

function listImages() {
    fetch('/api/list-images')
    .then(res => res.json())
    .then(images => {
        const list = document.getElementById('imageList');
        list.innerHTML = '';
        images.forEach(img => {
            const li = document.createElement('li');
            li.innerHTML = `<a href="#" onclick="viewImage('${img.imageId}')">${img.imageId}</a>`;
            list.appendChild(li);
        });
    })
    .catch(err => alert('Erro ao listar imagens: ' + err));
}

function viewImage(imageId) {
    fetch(`/api/view-image/${imageId}`)
    .then(res => res.json())
    .then(img => {
        const imageWindow = window.open("");
        imageWindow.document.write(`<img src="data:${img.content_type};base64,${img.base64_data}" />`);
    })
    .catch(err => alert('Erro ao recuperar imagem: ' + err));
}
