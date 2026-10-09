// ===================================================================
// CineIA — Frontend
// O navegador conversa somente com o backend Python.
// A API Key do Azure NÃO fica no JavaScript.
// ===================================================================

const statusConfig = document.getElementById('statusConfig');
const formChat = document.getElementById('formChat');
const campoMensagem = document.getElementById('campoMensagem');
const listaMensagens = document.getElementById('mensagens');


// Guarda o ID da última resposta para manter o contexto.
// O backend envia esse ID para a Responses API.
let ultimaRespostaId = null;


// ===================================================================
// VERIFICAR BACKEND
// ===================================================================

async function verificarBackend() {

  try {

    const resposta = await fetch('/api/health');

    const dados = await resposta.json();

    if (resposta.ok && dados.azure_configured) {
      statusConfig.textContent = 'Backend conectado à Azure ✅';
      return true;
    }

    statusConfig.textContent =
      'Backend funcionando, mas a Azure não está configurada.';

    return false;

  } catch (erro) {

    console.error('Erro ao verificar backend:', erro);

    statusConfig.textContent =
      'Backend offline ❌';

    return false;
  }
}


// ===================================================================
// ENVIAR MENSAGEM
// ===================================================================

formChat.addEventListener('submit', async (evento) => {

  evento.preventDefault();

  const texto = campoMensagem.value.trim();

  if (!texto) {
    return;
  }

  adicionarMensagemNaTela('user', texto);

  campoMensagem.value = '';

  const carregando = adicionarMensagemNaTela(
    'bot',
    'Pensando...'
  );

  const botaoEnviar = formChat.querySelector('button[type="submit"]');

  if (botaoEnviar) {
    botaoEnviar.disabled = true;
  }

  try {

    const resposta = await fetch('/api/chat', {

      method: 'POST',

      headers: {
        'Content-Type': 'application/json'
      },

      body: JSON.stringify({
        message: texto,
        previous_response_id: ultimaRespostaId
      })
    });


    const dados = await resposta.json();


    if (!resposta.ok) {

      throw new Error(
        dados.detail || 'Erro ao consultar o backend.'
      );
    }


    carregando.textContent = dados.response;


    // Guarda o ID para a próxima pergunta.
    ultimaRespostaId = dados.response_id || null;

  } catch (erro) {

    console.error('Erro no chat:', erro);

    carregando.textContent =
      `Não foi possível obter a resposta: ${erro.message}`;

  } finally {

    if (botaoEnviar) {
      botaoEnviar.disabled = false;
    }

    campoMensagem.focus();
  }
});


// ===================================================================
// ADICIONAR MENSAGEM NA TELA
// ===================================================================

function adicionarMensagemNaTela(remetente, texto) {

  const div = document.createElement('div');

  div.classList.add(
    'msg',
    remetente === 'user' ? 'user' : 'bot'
  );

  div.textContent = texto;

  listaMensagens.appendChild(div);

  listaMensagens.scrollTop = listaMensagens.scrollHeight;

  return div;
}


// ===================================================================
// INICIALIZAÇÃO
// ===================================================================

verificarBackend();
