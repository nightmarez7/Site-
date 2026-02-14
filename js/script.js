const button = document.getElementById("btn-submit");
const form = document.getElementById("forms-id");

emailjs.init("xEo3u50tozBEriJaK");

form.addEventListener("submit", function (e) {
  e.preventDefault();

  const dados = {
    email : document.getElementById("email").value.trim(),
    name : document.getElementById("name").value.trim(),
    assunto : document.getElementById("assunto").value.trim(),
    tel : document.getElementById("tel").value.trim(),
    message : document.getElementById("message").value.trim()
  };

  const vazio = Object.values(dados).some(valor => valor.trim() === "");

  if( vazio ) {
    alert("Insira todos os campos");
    return;
  }

  try {
    emailjs.send("service_avb3jdo", "template_zuj15zb", dados)
    alert("Email enviado");
    form.reset();

  } catch(erro) {
    alert("Erro ao enviar");
  }
});