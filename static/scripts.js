function uploadImage() {
    const fileInput = document.getElementById('fileUpload');
    const file = fileInput.files[0];

    if (!file) {
        alert('Selecione um arquivo antes de enviar!');
        return;
    }

    // 🔒 Validação do tipo de arquivo
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
        alert('Apenas arquivos PNG, JPG e JPEG são permitidos!');
        return;
    }

    fetch('/api/upload-url', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            'filename': file.name,
            'contentType': file.type || 'application/octet-stream'
        })
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
        const viewer = document.getElementById('imageViewer');
        viewer.innerHTML = `
            <h3>Visualizando: ${imageId}</h3>
            <img src="data:${img.content_type};base64,${img.base64_data}" 
                 alt="${imageId}" 
                 style="max-width: 100%; border-radius: 8px; margin-top: 10px;">
        `;
        viewer.scrollIntoView({ behavior: 'smooth' });
    })
    .catch(err => alert('Erro ao recuperar imagem: ' + err));
}
