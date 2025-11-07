// CONCURSOIA - Sistema Inteligente de Estudos (v4.0 - CORRIGIDO)
let simuladoAtual = null;
let questaoAtual = null;
let simuladoTimerInterval = null; // (NOVO) Variável global do cronômetro

// Sistema de Cache Local
const SessionManager = {
    set: function(key, value) {
        try {
            sessionStorage.setItem("concursoia_" + key, JSON.stringify(value));
        } catch (e) {
            console.warn("Erro ao salvar sessão:", e);
        }
    },

    get: function(key) {
        try {
            const stored = sessionStorage.getItem("concursoia_" + key);
            return stored ? JSON.parse(stored) : null;
        } catch (e) {
            console.warn("Erro ao recuperar sessão:", e);
            return null;
        }
    },

    remove: function(key) {
        try {
            sessionStorage.removeItem("concursoia_" + key);
        } catch (e) {
            console.warn("Erro ao remover sessão:", e);
        }
    }
};

// Funções de Carregamento
function carregarConteudoInicial() {
    carregarAreas();
    carregarBancas();
    // carregarTemasRedacao(); // Removido, pois navegarPara('tela-redacao') fará isso
}

function carregarBancas() {
    fetch("/api/bancas")
    .then(response => {
        if (!response.ok) { throw new Error('Erro 404 ou 500 na API /api/bancas'); }
        return response.json();
    })
    .then(data => {
        if (data.success && data.bancas) {
            exibirBancas(data.bancas);
        } else {
            throw new Error(data.error || "Formato de dados de bancas inesperado.");
        }
    })
    .catch(error => {
        console.error("Erro ao carregar bancas:", error);
        exibirBancas([]); 
    });
}

function carregarAreas() {
    fetch("/api/areas")
    .then(response => {
        if (!response.ok) { throw new Error('Erro 404 ou 500 na API /api/areas'); }
        return response.json();
    })
    .then(data => {
        if (data.success && data.areas) {
            exibirAreas(data.areas);
        } else {
            throw new Error(data.error || "Formato de dados de áreas inesperado.");
        }
    })
    .catch(error => {
        console.error("Erro ao carregar áreas:", error);
        const container = document.getElementById("materias-container");
        if (container) {
            container.innerHTML = '<p class="no-data">Erro ao carregar áreas. Tente recarregar a página.</p>';
        }
    });
}

function carregarTemasRedacao() {
    // Esta função foi substituída por carregarTemasMelhorados()
    // Mas a manteremos por enquanto, caso a nova falhe
    console.warn("Chamando carregarTemasRedacao() antigo. Use carregarTemasMelhorados().");
    
    fetch("/api/redacao/temas") // Pode ser a rota antiga ou a nova, o app.py redireciona
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const select = document.getElementById("temas-redacao");
            if (!select) return;

            select.innerHTML = '<option value="">Selecione um tema</option>';

            data.temas.forEach(tema => {
                const option = document.createElement("option");
                option.value = tema.titulo;
                option.textContent = tema.titulo;
                // (NOVO) Adiciona os dados para a função melhorada
                option.dataset.enunciado = tema.enunciado || "Enunciado padrão...";
                option.dataset.textosBase = JSON.stringify(tema.textos_base || []);
                select.appendChild(option);
            });
        }
    })
    .catch(error => {
        console.error("Erro na API de Redação:", error);
    });
}

// Navegação
function navegarPara(tela) {
    document.querySelectorAll(".tela").forEach(t => {
        t.classList.add("hidden");
    });

    const telaElement = document.getElementById(tela);
    if (telaElement) {
        telaElement.classList.remove("hidden");
    }

    document.querySelectorAll(".nav-tab").forEach(tab => {
        tab.classList.remove("active");
    });
    
    const navTab = document.querySelector('.nav-tab[onclick*="' + tela + '"]');
    if (navTab) {
        navTab.classList.add("active");
    }

    // Lógica de carregamento de conteúdo específico da tela
    if (tela === "tela-simulado") {
        // (INÍCIO DA ALTERAÇÃO) - Lógica de navegação do simulado
        const selecaoContainer = document.getElementById("selecao-simulado");
        const simuladoAtivoContainer = document.getElementById("simulado-ativo");
        const resultado = document.getElementById("tela-resultado");
        
        // Verifica se há um simulado ativo na sessão
        const simuladoIDs = SessionManager.get('simulado_ids');
        
        if (simuladoIDs && simuladoIDs.length > 0) {
            // Se sim, mostre o simulado ativo e esconda o resto
            if (selecaoContainer) selecaoContainer.classList.add("hidden");
            if (simuladoAtivoContainer) simuladoAtivoContainer.classList.remove("hidden");
            if (resultado) resultado.classList.add("hidden");
            iniciarCronometro(); // Retoma o cronômetro ao voltar para a aba
        } else {
            // Se não, mostre a seleção (comportamento padrão)
            if (selecaoContainer) selecaoContainer.classList.remove("hidden");
            if (simuladoAtivoContainer) simuladoAtivoContainer.classList.add("hidden");
            if (resultado) resultado.classList.add("hidden");
            carregarAreas();
            carregarBancas();
            pararCronometro(); // Garante que qualquer timer órfão seja limpo
        }
        // (FIM DA ALTERAÇÃO)

    } else if (tela === "tela-redacao") {
        // (ALTERADO) - Carrega os temas melhorados
        // carregarTemasRedacao(); // Antigo
        carregarTemasMelhorados(); // Novo
        setTimeout(exibirDicasRedacao, 100);
    } else if (tela === "tela-dashboard") {
        // (ALTERADO) - Carrega o dashboard simplificado
        // carregarDashboard(); // Antigo
        carregarDashboardSimplificado(); // Novo
    }
}

// SIMULADO - Funções
function iniciarSimulado() {
    // Lê TODOS os checkboxes (simples e sub-áreas)
    const areasSelecionadas = Array.from(
        document.querySelectorAll("#materias-container .area-checkbox-simple:checked, #materias-container .sub-area-checkbox:checked")
    ).map(cb => cb.value);
    
    const bancaSelecionada = document.getElementById("select-banca").value;
    const quantidade = document.getElementById("quantidade-questoes").value;

    if (areasSelecionadas.length === 0) {
        alert("Selecione pelo menos uma Matéria ou Área de Estudo!");
        return;
    }

    const selecaoContainer = document.getElementById("selecao-simulado");
    const simuladoAtivoContainer = document.getElementById("simulado-ativo");

    if (selecaoContainer) selecaoContainer.classList.add("hidden");
    if (simuladoAtivoContainer) {
         simuladoAtivoContainer.classList.remove("hidden");
         simuladoAtivoContainer.innerHTML = '<div class="card"><div class="text-center"><div class="loading"></div><p>Preparando seu simulado...</p></div></div>';
    }

    // (NOVO) Limpa o cronômetro antigo antes de buscar um novo
    pararCronometro();
    SessionManager.remove('simuladoStartTime');

    fetch("/api/simulado/iniciar", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            areas: areasSelecionadas,
            banca: bancaSelecionada,
            quantidade: quantidade 
        })
    })
    .then(response => {
        if (!response.ok) {
             return response.json().then(errData => {
                 throw new Error(errData.error || "Erro na resposta do servidor: " + response.status);
             }).catch(() => {
                 throw new Error("Erro na resposta do servidor: " + response.status);
             });
        }
        return response.json();
    })
    .then(data => {
        if (data.success && data.questao) {
            simuladoAtual = {
                indice_atual: data.indice_atual,
                total_questoes: data.total_questoes
            };
            
            mostrarTelaSimuladoAtivo(data.total_questoes);
            exibirQuestao(data.questao, data.indice_atual, data.total_questoes, data.resposta_anterior);
            
            // (NOVO) Inicia o cronômetro
            iniciarCronometro();
        } else {
            alert("Erro ao iniciar simulado: " + (data.error || "Nenhuma questão encontrada."));
            if (selecaoContainer) selecaoContainer.classList.remove("hidden");
            if (simuladoAtivoContainer) simuladoAtivoContainer.classList.add("hidden");
        }
    })
    .catch(error => {
        console.error("Erro:", error);
        alert("Erro ao iniciar simulado: " + error.message);
        if (selecaoContainer) selecaoContainer.classList.remove("hidden");
        if (simuladoAtivoContainer) simuladoAtivoContainer.classList.add("hidden");
    });
}

// BOTÕES DO SIMULADO
function mostrarTelaSimuladoAtivo(totalQuestoes) {
    const selecaoContainer = document.getElementById("selecao-simulado");
    const simuladoAtivoContainer = document.getElementById("simulado-ativo");
    
    if (selecaoContainer) selecaoContainer.classList.add("hidden");
    if (simuladoAtivoContainer) {
        simuladoAtivoContainer.classList.remove("hidden");
        
        // (INÍCIO DA ALTERAÇÃO) - HTML atualizado com as novas features
        simuladoAtivoContainer.innerHTML = 
        `<div class="card questao-container">
            
            <div class="simulado-controls-bar">
                <div class="cronometro-container">
                    <span class="cronometro-icon">⏱️</span>
                    <span id="cronometro-display">00:00:00</span>
                </div>
                
                <div class="simulado-tools">
                    <div class="font-controls">
                        <span class="font-label">Fonte:</span>
                        <button id="btn-font-decrease" class="btn-font-control" title="Diminuir Fonte">A-</button>
                        <button id="btn-font-increase" class="btn-font-control" title="Aumentar Fonte">A+</button>
                    </div>
                    <button id="btn-focus-mode" class="btn-font-control" title="Modo Foco">
                        <span id="focus-icon-expand">⛶</span>
                        <span id="focus-icon-compress" class="hidden">↘</span>
                    </button>
                </div>
            </div>
            <div class="questao-header">
                <div>
                    <h3 id="questao-numero">Questão 1 de ${totalQuestoes}</h3>
                    <div class="questao-info">
                        <span class="questao-tag" id="questao-disciplina">-</span>
                        <span class="questao-tag" id="questao-materia">-</span>
                        <span class="questao-tag" id="questao-dificuldade">-</span>
                    </div>
                </div>
            </div>
            <div class="progresso-container">
                <div id="progresso-simulado" class="progresso-bar"></div>
            </div>

            <div id="simulado-content-zoomavel">
                <div class="questao-content-wrapper">
                    <div class="questao-enunciado-container">
                        <div class="questao-enunciado" id="questao-enunciado">Carregando questão...</div>
                    </div>
                    <div class="questao-auxiliar" id="questao-auxiliar">
                        <div class="auxiliar-vazio">Nenhuma informação auxiliar para esta questão.</div>
                    </div>
                </div>
                <div class="alternativas-container" id="questao-alternativas"></div>
                <div id="feedback-questao" style="display: none;"></div>
            </div>
            <div class="simulado-navigation-profissional">
                <div class="nav-group-left">
                    <button id="btn-anterior" class="btn btn-anterior" onclick="mudarQuestao(-1)" disabled>
                        <span class="btn-icon">←</span> Anterior
                    </button>
                </div>
                
                <div class="nav-group-center">
                    <button class="btn btn-responder-profissional" onclick="responderQuestao()">
                        <span class="btn-icon">✓</span> Responder
                    </button>
                </div>
                
                <div class="nav-group-right">
                    <button id="btn-proximo" class="btn btn-proximo" onclick="mudarQuestao(1)">
                        Próxima <span class="btn-icon">→</span>
                    </button>
                    <button id="btn-finalizar-geral" class="btn btn-finalizar" onclick="finalizarSimulado()">
                        <span class="btn-icon">⏹</span> Finalizar
                    </button>
                </div>
            </div>
        </div>`;
        // (FIM DA ALTERAÇÃO)
        
        // (NOVO) Aplica preferências salvas (modo foco) assim que o HTML é criado
        aplicarPreferenciasSalvas();
    }
}

function exibirQuestao(questao, indice, total, respostaAnterior) {
    questaoAtual = questao;

    document.getElementById("questao-numero").textContent = "Questão " + (indice + 1) + " de " + total;
    document.getElementById("questao-disciplina").textContent = questao.disciplina;
    document.getElementById("questao-materia").textContent = questao.materia;
    document.getElementById("questao-dificuldade").textContent = questao.dificuldade || "Média";
    document.getElementById("questao-enunciado").innerHTML = questao.enunciado;

    atualizarProgresso(indice, total);

    // Área auxiliar com cards
    const auxiliarElement = document.getElementById("questao-auxiliar");
    if (auxiliarElement) {
        let auxiliarHTML = '';

        if (questao.dica && questao.dica !== "N/A" && questao.dica !== "") {
            auxiliarHTML += 
            `<div class="auxiliar-card dica-card">
                <div class="auxiliar-header">
                    <span class="auxiliar-icon">💡</span>
                    <h4>Dica</h4>
                </div>
                <div class="auxiliar-content">
                    ${questao.dica}
                </div>
            </div>`;
        }

        if (questao.formula && questao.formula !== "N/A" && questao.formula !== "") {
            auxiliarHTML += 
            `<div class="auxiliar-card formula-card">
                <div class="auxiliar-header">
                    <span class="auxiliar-icon">📐</span>
                    <h4>Fórmula</h4>
                </div>
                <div class="auxiliar-content">
                    ${questao.formula}
                </div>
            </div>`;
        }

        if (auxiliarHTML === '') {
            auxiliarHTML = '<div class="auxiliar-vazio">Nenhuma informação auxiliar para esta questão.</div>';
        }

        auxiliarElement.innerHTML = auxiliarHTML;
    }

    // Alternativas
    const alternativasContainer = document.getElementById("questao-alternativas");
    if (alternativasContainer) {
        alternativasContainer.innerHTML = '';

        Object.entries(questao.alternativas).forEach(([letra, texto]) => {
            if (letra === "e" && (texto === null || texto === "" || texto === undefined)) {
                return;
            }
            
            // (CORREÇÃO) Garante que mesmo alternativas nulas sejam tratadas
            if (texto === null || texto === undefined) {
                texto = "";
            }

            const alternativaDiv = document.createElement("div");
            alternativaDiv.className = "alternativa";

            const isSelected = respostaAnterior && (respostaAnterior.alternativa_escolhida === letra);
            const disabledAttr = respostaAnterior ? "disabled" : "";

            alternativaDiv.innerHTML = 
            `<input type="radio" name="alternativa" id="alt-${letra}" value="${letra}" ${disabledAttr}>
            <label for="alt-${letra}">
                <span class="letra-alternativa">${letra.toUpperCase()})</span>
                ${texto}
            </label>`;

            alternativaDiv.onclick = function() {
                if (respostaAnterior) return;
                this.querySelector("input[type='radio']").checked = true;
                alternativasContainer.querySelectorAll(".alternativa").forEach(alt => {
                    alt.classList.remove("selected");
                });
                this.classList.add("selected");
            };

            if (isSelected) {
                alternativaDiv.classList.add("selected");
            }

            alternativasContainer.appendChild(alternativaDiv);
        });
    }

    // Feedback da questão anterior
    if (respostaAnterior) {
        const feedbackData = {
             acertou: respostaAnterior.acertou,
             resposta_correta: questao.resposta_correta.toUpperCase(),
             justificativa: questao.justificativa
        };
        mostrarFeedbackQuestao(feedbackData);
        desabilitarInteracaoQuestao();
    } else {
        const feedbackQuestao = document.getElementById("feedback-questao");
        if(feedbackQuestao) feedbackQuestao.style.display = "none";
        habilitarInteracaoQuestao();
    }

    // Controles de navegação
    const btnAnterior = document.getElementById("btn-anterior");
    if (btnAnterior) {
        btnAnterior.disabled = indice === 0;
    }

    const btnProximo = document.getElementById("btn-proximo");
    if (btnProximo) {
        btnProximo.style.display = indice < total - 1 ? "inline-block" : "none";
    }

    // (NOVO) Garante que o zoom seja aplicado ao carregar a questão
    const savedSize = SessionManager.get('fontSize');
    const content = document.getElementById('simulado-content-zoomavel');
    if (savedSize && content) {
        // Define o font-size com base no valor salvo
        content.style.fontSize = parseFloat(savedSize) + "em";
    } else if (content) {
        // Garante que o padrão seja 1em se nada estiver salvo
        content.style.fontSize = "1.0em"; 
    }
}

function atualizarProgresso(indice, total) {
    // (CORREÇÃO) Evita divisão por zero se o total for 0
    const totalQuestoes = total > 0 ? total : 1;
    const progresso = ((indice + 1) / totalQuestoes) * 100;
    const progressBar = document.getElementById("progresso-simulado");
    if (progressBar) {
        progressBar.style.width = progresso + "%";
    }
}

function mudarQuestao(direcao) {
    if (!simuladoAtual) {
        alert("Nenhum simulado ativo!");
        return;
    }

    const indiceAtual = simuladoAtual.indice_atual || 0;
    const novoIndice = indiceAtual + direcao;

    if (novoIndice < 0 || novoIndice >= simuladoAtual.total_questoes) {
        return;
    }

    fetch("/api/simulado/questao/" + novoIndice)
    .then(response => {
        if (!response.ok) {
            throw new Error("Erro ao buscar questão: " + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            simuladoAtual.indice_atual = novoIndice;
            exibirQuestao(data.questao, novoIndice, data.total_questoes, data.resposta_anterior);
        } else {
            alert("Erro: " + data.error);
        }
    })
    .catch(error => {
        console.error("Erro:", error);
        alert("Erro ao navegar entre questões: " + error.message);
    });
}

function responderQuestao() {
    if (!questaoAtual) {
        alert("Nenhuma questão carregada!");
        return;
    }

    const alternativaSelecionada = document.querySelector('input[name="alternativa"]:checked');

    if (!alternativaSelecionada) {
        alert("Selecione uma alternativa!");
        return;
    }

    fetch("/api/simulado/responder", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            questao_id: questaoAtual.id,
            alternativa: alternativaSelecionada.value
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Erro na resposta: " + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            mostrarFeedbackQuestao(data);
            desabilitarInteracaoQuestao();
        } else {
            alert("Erro: " + data.error);
        }
    })
    .catch(error => {
        console.error("Erro ao responder:", error);
        alert("Erro ao responder questão: " + error.message);
    });
}

function mostrarFeedbackQuestao(data) {
    const feedback = document.getElementById("feedback-questao");
    if (feedback) {
        let feedbackHTML = '<div class="feedback ' + (data.acertou ? "acerto" : "erro") + '">';
        feedbackHTML += '<h4>' + (data.acertou ? "✅ Acertou!" : "❌ Errou!") + "</h4>";
        feedbackHTML += '<p><strong>Resposta correta:</strong> ' + data.resposta_correta + "</p>";

        if (!data.acertou && data.justificativa) {
             feedbackHTML += '<p><strong>Explicação:</strong> ' + data.justificativa + "</p>";
        }

        feedbackHTML += "</div>";
        feedback.innerHTML = feedbackHTML;
        feedback.style.display = "block";
    }
}

function desabilitarInteracaoQuestao() {
    document.querySelectorAll(".alternativas-container input[type='radio']").forEach(input => {
        input.disabled = true;
    });
    const btnResponder = document.querySelector(".btn-responder-profissional");
    if (btnResponder) {
        btnResponder.disabled = true;
    }
}

function habilitarInteracaoQuestao() {
    document.querySelectorAll(".alternativas-container input[type='radio']").forEach(input => {
        input.disabled = false;
    });
    const btnResponder = document.querySelector(".btn-responder-profissional");
    if (btnResponder) {
        btnResponder.disabled = false;
    }
}

function finalizarSimulado() {
    if (!simuladoAtual) {
        alert("Nenhum simulado ativo para finalizar!");
        return;
    }

    if (!confirm("Tem certeza que deseja finalizar o simulado agora?")) {
        return;
    }

    // (NOVO) Para o cronômetro
    pararCronometro();

    const simuladoContainer = document.getElementById("simulado-ativo");
    if (simuladoContainer) {
        simuladoContainer.innerHTML = '<div class="text-center"><div class="loading"></div><p>Finalizando simulado e gerando resultados...</p></div>';
    }

    fetch("/api/simulado/finalizar", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Erro na resposta: " + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // (NOVO) Limpa o cronômetro da sessão
            SessionManager.remove('simuladoStartTime');
            exibirResultado(data.relatorio);
        } else {
            alert("Erro: " + data.error);
            // (NOVO) Reinicia o cronômetro se a finalização falhar
            iniciarCronometro(); 
        }
    })
    .catch(error => {
        console.error("Erro na finalização:", error);
        alert("Erro ao finalizar simulado: " + error.message);
        // (NOVO) Reinicia o cronômetro se a finalização falhar
        iniciarCronometro();
    });
}

function exibirResultado(relatorio) {
    document.getElementById("resultado-acertos").textContent = relatorio.total_acertos + "/" + relatorio.total_questoes;
    document.getElementById("resultado-percentual").textContent = relatorio.percentual_acerto + "%";
    document.getElementById("resultado-nota").textContent = relatorio.nota_final; // Removido %

    const simuladoAtivo = document.getElementById("simulado-ativo");
    const resultado = document.getElementById("tela-resultado");
    if (simuladoAtivo) simuladoAtivo.classList.add("hidden");
    if (resultado) resultado.classList.remove("hidden");
}

// REDAÇÃO (ANTIGA)
function corrigirRedacao() {
    // Esta função foi substituída por corrigirRedacaoGeminiReal()
    console.warn("Chamando corrigirRedacao() antigo. Usando corrigirRedacaoGeminiReal().");
    corrigirRedacaoGeminiReal();
}

function exibirCorrecaoRedacao(correcao) {
    // Esta função foi substituída por exibirCorrecaoRedacaoAvancada()
    // Mantida para exibir a versão antiga caso a nova falhe
    console.warn("Chamando exibirCorrecaoRedacao() antigo. Use exibirCorrecaoRedacaoAvancada().");

    const resultadoDiv = document.getElementById("resultado-correcao");

    let html = '<div class="card resultado-header">' +
        '<div class="nota-container">' +
            '<h3>📊 Resultado da Correção (Antigo)</h3>' +
            '<div class="nota-final">' + (correcao.nota_final || 0) + "/100</div>" +
            // ... (restante do HTML antigo)
        "</div>" +
    "</div>";
    
    // ... (restante do HTML antigo)

    if (resultadoDiv) {
        resultadoDiv.innerHTML = html;
        resultadoDiv.classList.remove("hidden");
        resultadoDiv.scrollIntoView({ behavior: "smooth" });
    }
}

// DICAS DE REDAÇÃO
function exibirDicasRedacao() {
    const container = document.getElementById("dicas-redacao");
    if (!container) return;

    const dicasHTML = `
        <div class="dicas-redacao-lateral">
            <div class="dica-card-redacao">
                <div class="dica-header-redacao">
                    <span class="dica-icon">📝</span>
                    <h4>Como Estruturar sua Redação</h4>
                </div>
                <div class="dica-content-redacao">
                    <p><strong>Introdução (1 parágrafo):</strong></p>
                    <ul>
                        <li>Apresente o tema</li>
                        <li>Contextualize o problema</li>
                        <li>Apresente sua tese</li>
                    </ul>
                    
                    <p><strong>Desenvolvimento (2-3 parágrafos):</strong></p>
                    <ul>
                        <li>Argumento 1 + repertório</li>
                        <li>Argumento 2 + repertório</li>
                        <li>Analise crítica dos argumentos</li>
                    </ul>
                    
                    <p><strong>Conclusão (1 parágrafo):</strong></p>
                    <ul>
                        <li>Retome a tese</li>
                        <li>Proposta de intervenção completa (5 elementos)</li>
                    </ul>
                </div>
            </div>

            <div class="dica-card-redacao">
                <div class="dica-header-redacao">
                    <span class="dica-icon">🎯</span>
                    <h4>Intervenção (Competência 5)</h4>
                </div>
                <div class="dica-content-redacao">
                    <p>Sua proposta deve ter 5 elementos:</p>
                    <ul>
                        <li><strong>Agente:</strong> Quem vai fazer? (Ex: Governo Federal)</li>
                        <li><strong>Ação:</strong> O que será feito? (Ex: Criar campanhas)</li>
                        <li><strong>Modo/Meio:</strong> Como será feito? (Ex: Por meio de mídias)</li>
                        <li><strong>Efeito:</strong> Para que será feito? (Ex: A fim de conscientizar)</li>
                        <li><strong>Detalhamento:</strong> (Explicar um dos elementos acima)</li>
                    </ul>
                </div>
            </div>

            <div class="dica-card-redacao">
                <div class="dica-header-redacao">
                    <span class="dica-icon">⚠️</span>
                    <h4>O que Evitar (Nota Zero)</h4>
                </div>
                <div class="dica-content-redacao">
                    <ul>
                        <li>Fugir totalmente do tema</li>
                        <li>Texto com menos de 7 linhas</li>
                        <li>Cópia integral dos textos de apoio</li>
                        <li>Desenhos ou xingamentos</li>
                        <li>Desrespeitar os direitos humanos</li>
                    </ul>
                </div>
            </div>
        </div>
    `;

    container.innerHTML = dicasHTML;
}

// DASHBOARD (ANTIGO)
function carregarDashboard() {
    // Esta função foi substituída por carregarDashboardSimplificado()
    console.warn("Chamando carregarDashboard() antigo. Use carregarDashboardSimplificado().");
    carregarDashboardSimplificado();
}

function exibirDashboardPorArea(data) {
    // Esta função foi substituída por exibirDashboardSimplificado()
    // Mantida apenas como fallback
    console.warn("Chamando exibirDashboardPorArea() antigo.");
    
    const container = document.getElementById("dashboard-content");
    if (!container) return;

    const stats = data.stats_gerais;

    let html = '<div class="dashboard-header">' +
        '<h3>📈 Dashboard de Desempenho (Antigo)</h3>' +
    "</div>";
    
    // ... (restante do HTML antigo)
    
    container.innerHTML = html;
}

// FUNÇÕES DE EXIBIÇÃO - COMPORTAMENTO INTELIGENTE
function exibirBancas(bancas) {
    const selectBanca = document.getElementById("select-banca");
    if (!selectBanca) return;
    
    let optionsHTML = ''; // Removido o "Todas as Bancas" daqui
    
    if (bancas && bancas.length > 0) {
         bancas.forEach(banca => {
            // (MELHORADO) - A opção "(Banca Padrão)" vem da API
            optionsHTML += '<option value="' + banca.banca + '">' + banca.banca + ' (' + banca.total_questoes + ' Q)</option>';
        });
    }

    selectBanca.innerHTML = optionsHTML;
}

// COMPORTAMENTO INTELIGENTE - ÁREAS DE ESTUDO
function exibirAreas(areas) {
    const container = document.getElementById("materias-container");
    if (!container) return;

    container.innerHTML = '';

    if (!areas || !Array.isArray(areas) || areas.length === 0) {
        container.innerHTML = '<p class="no-data">Nenhuma área de estudo encontrada.</p>';
        return;
    }

    const grid = document.createElement("div");
    grid.className = "areas-grid-inteligente";

    areas.forEach(area => {
        const isMultiplo = area.sub_materias.length > 1;
        
        const card = document.createElement("div");
        card.className = "area-card-inteligente";
        card.dataset.areaId = area.area_principal.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
        
        if (isMultiplo) {
            // ÁREAS COM MÚLTIPLAS SUBMATÉRIAS
            card.innerHTML = `
                <div class="area-header" onclick="toggleAreaSelection(this, true)">
                    <span class="area-card-icon">${getIconeArea(area.area_principal)}</span>
                    <div class="area-info">
                        <h4 class="area-title">${area.area_principal}</h4>
                        <span class="area-count">${area.total_questoes} questões</span>
                    </div>
                    <div class="area-controls">
                        <span class="expand-icon">▶</span>
                    </div>
                </div>
                <div class="sub-areas-container hidden">
                    ${area.sub_materias.map(sub => `
                        <label class="sub-area-item" onclick="event.stopPropagation()">
                            <input type="checkbox" value="${sub}" class="sub-area-checkbox" 
                                   onchange="updateAreaState('${area.area_principal.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}')">
                            <span class="sub-area-label">${sub}</span>
                        </label>
                    `).join('')}
                </div>
            `;
        } else {
            // ÁREAS COM APENAS 1 SUBMATÉRIA
            card.innerHTML = `
                <div class="area-header" onclick="toggleAreaSelection(this, false)">
                    <span class="area-card-icon">${getIconeArea(area.area_principal)}</span>
                    <div class="area-info">
                        <h4 class="area-title">${area.area_principal}</h4>
                        <span class="area-count">${area.total_questoes} questões</span>
                    </div>
                    <div class="area-controls">
                        <input type="checkbox" class="area-checkbox-simple" value="${area.sub_materias[0]}" 
                               onchange="event.stopPropagation()">
                    </div>
                </div>
            `;
            
            // Para áreas simples, o checkbox controla o estado visual
            const checkbox = card.querySelector('.area-checkbox-simple');
            checkbox.addEventListener('change', function() {
                card.classList.toggle('selected', this.checked);
            });
        }

        grid.appendChild(card);
    });

    container.appendChild(grid);
}

// FUNÇÃO: Alternar seleção de área
function toggleAreaSelection(headerElement, isMultiplo) {
    const card = headerElement.closest('.area-card-inteligente');
    
    if (isMultiplo) {
        // Área com múltiplas submatérias - expandir/recolher
        const subContainer = card.querySelector('.sub-areas-container');
        const expandIcon = card.querySelector('.expand-icon');
        
        subContainer.classList.toggle('hidden');
        card.classList.toggle('expanded');
        
        // Se estiver expandindo, atualiza o estado visual
        if (!subContainer.classList.contains('hidden')) {
            updateAreaState(card.dataset.areaId);
        }
    } else {
        // Área com 1 submatéria - selecionar/desselecionar diretamente
        const checkbox = card.querySelector('.area-checkbox-simple');
        checkbox.checked = !checkbox.checked;
        checkbox.dispatchEvent(new Event('change'));
    }
}

// FUNÇÃO: Atualizar estado da área (múltiplas submatérias)
function updateAreaState(areaId) {
    const card = document.querySelector(`[data-area-id="${areaId}"]`);
    if (!card) return; // (CORREÇÃO) Evita erro se o card não for encontrado
    const checkboxes = card.querySelectorAll('.sub-area-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    const someChecked = Array.from(checkboxes).some(cb => cb.checked);
    
    // Atualizar estado visual do card
    card.classList.toggle('selected', allChecked);
    card.classList.toggle('partial', someChecked && !allChecked);
}

// FUNÇÃO: Selecionar todas as submatérias de uma área
function selectAllSubAreas(areaId, select) {
    const card = document.querySelector(`[data-area-id="${areaId}"]`);
    if (!card) return; // (CORREÇÃO)
    const checkboxes = card.querySelectorAll('.sub-area-checkbox');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = select;
    });
    
    updateAreaState(areaId);
}

function getIconeArea(areaNome) {
    const icones = {
        "Língua Portuguesa": "📝",
        "Exatas e Raciocínio Lógico": "🔢",
        "Conhecimentos Jurídicos": "⚖️",
        "Conhecimentos Bancários e Vendas": "💰",
        "Psicologia Clínica e Saúde": "🧠",
        "Gestão de Pessoas": "👥",
        "Informática": "💻",
        "Atualidades Gerais": "📰",
        "Matemática": "🔢",
        "Raciocínio Lógico": "🔢",
        "Matemática Financeira": "🔢",
        "Direito Administrativo": "⚖️",
        "Direito Constitucional": "⚖️",
        "Psicologia": "🧠",
        "Psicologia (Saúde)": "🧠",
        "Psicologia (Gestão)": "👥"
    };
    return icones[areaNome] || "❓";
}

// Inicialização
document.addEventListener("DOMContentLoaded", function() {
    console.log("🚀 ConcursoIA v4.0 (Tema Original) inicializado");
    // Limpa cache de sessões antigas
    SessionManager.remove("simulado_questoes");
    SessionManager.remove("simulado_respostas");
    SessionManager.remove("indice_atual");
    
    // (NOVO) Aplica Focus Mode e Font Size salvos
    aplicarPreferenciasSalvas();
    
    // (NOVO) Adiciona listeners para os novos botões
    adicionarListenersSimulado();
    
    carregarConteudoInicial();
    navegarPara("tela-inicio"); // Inicia na tela de início
});


// ============================================================================
// (NOVAS FUNÇÕES - CRONÔMETRO, FONTE, MODO FOCO)
// ============================================================================

function iniciarCronometro() {
    pararCronometro(); // Garante que não haja timers duplicados
    
    let startTime = SessionManager.get('simuladoStartTime');
    if (!startTime) {
        startTime = new Date().getTime();
        SessionManager.set('simuladoStartTime', startTime);
    }
    
    simuladoTimerInterval = setInterval(atualizarCronometro, 1000);
    atualizarCronometro(); // Chama imediatamente para não esperar 1s
}

function pararCronometro() {
    if (simuladoTimerInterval) {
        clearInterval(simuladoTimerInterval);
        simuladoTimerInterval = null;
    }
    // Nota: Não remove o 'simuladoStartTime' da sessão aqui,
    // apenas 'finalizarSimulado()' deve fazer isso.
}

function atualizarCronometro() {
    const startTime = SessionManager.get('simuladoStartTime');
    if (!startTime) return;
    
    const display = document.getElementById('cronometro-display');
    if (!display) {
        pararCronometro(); // Para o timer se o display sumir
        return;
    }

    const now = new Date().getTime();
    const elapsed = Math.floor((now - startTime) / 1000); // em segundos

    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;

    display.textContent = 
        (hours < 10 ? '0' : '') + hours + ':' +
        (minutes < 10 ? '0' : '') + minutes + ':' +
        (seconds < 10 ? '0' : '') + seconds;
}

function aplicarPreferenciasSalvas() {
    // Aplica Focus Mode se salvo
    const isFocused = SessionManager.get('focusMode') === true;
    if (isFocused) {
        document.body.classList.add('focus-mode');
    }
    
    // Atualiza ícones (mesmo que o HTML não esteja pronto, 
    // será corrigido quando mostrarTelaSimuladoAtivo for chamado)
    const iconExpand = document.getElementById('focus-icon-expand');
    const iconCompress = document.getElementById('focus-icon-compress');
    if(iconExpand && iconCompress){
        iconExpand.classList.toggle('hidden', isFocused);
        iconCompress.classList.toggle('hidden', !isFocused);
    }

    // Aplica Font Size
    // Nota: O elemento '#simulado-content-zoomavel' pode não existir ainda.
    // A função 'exibirQuestao' também chama essa lógica para garantir.
    const savedSize = SessionManager.get('fontSize');
    const content = document.getElementById('simulado-content-zoomavel');
    if (savedSize && content) {
        content.style.fontSize = parseFloat(savedSize) + "em";
    }
}

function adicionarListenersSimulado() {
    // Usamos delegação de eventos no 'body' para que os botões 
    // funcionem mesmo sendo criados dinamicamente.
    document.body.addEventListener('click', function(e) {
        
        const targetId = e.target.id || (e.target.closest('button') ? e.target.closest('button').id : null);
        
        // --- Controle de Fonte ---
        const content = document.getElementById('simulado-content-zoomavel');
        
        if (targetId === 'btn-font-increase' || targetId === 'btn-font-decrease') {
            if (!content) return; // Só age se o simulado estiver na tela

            let currentSize = 1.0;
            const savedSize = SessionManager.get('fontSize');
            if (savedSize) {
                currentSize = parseFloat(savedSize);
            } else {
                // Tenta ler do estilo, convertendo px para em (base 16px)
                const computedSize = parseFloat(window.getComputedStyle(content).fontSize) / 16;
                if (!isNaN(computedSize) && computedSize > 0) {
                    currentSize = computedSize;
                }
            }

            if (targetId === 'btn-font-increase') {
                if (currentSize < 1.6) { // Limite de 160%
                    currentSize = (currentSize * 10 + 1) / 10; // Evita bugs de ponto flutuante
                    content.style.fontSize = currentSize + "em";
                    SessionManager.set('fontSize', currentSize);
                }
            }

            if (targetId === 'btn-font-decrease') {
                if (currentSize > 0.8) { // Limite de 80%
                    currentSize = (currentSize * 10 - 1) / 10;
                    content.style.fontSize = currentSize + "em";
                    SessionManager.set('fontSize', currentSize);
                }
            }
        }
        
        // --- Modo Foco ---
        if (targetId === 'btn-focus-mode') {
            const isFocused = document.body.classList.toggle('focus-mode');
            SessionManager.set('focusMode', isFocused);
            
            // Troca os ícones
            const iconExpand = document.getElementById('focus-icon-expand');
            const iconCompress = document.getElementById('focus-icon-compress');
            if(iconExpand && iconCompress){
                iconExpand.classList.toggle('hidden', isFocused);
                iconCompress.classList.toggle('hidden', !isFocused);
            }
        }
    });
}


// ============================================================================
// 🎯 (NOVO) DASHBOARD SIMPLIFICADO - FOCADO EM METAS
// ============================================================================

function carregarDashboardSimplificado() {
    const container = document.getElementById("dashboard-content");
    if (!container) return;
    container.innerHTML = '<div class="text-center"><div class="loading"></div><p style="color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">Carregando seu progresso...</p></div>'; // Texto branco

    fetch('/api/dashboard/simplificado')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                exibirDashboardSimplificado(data);
            } else {
                document.getElementById('dashboard-content').innerHTML = `<p class="text-center" style="color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">Erro ao carregar dashboard: ${data.error}</p>`;
            }
        })
        .catch(error => {
            console.error('Erro no dashboard:', error);
            document.getElementById('dashboard-content').innerHTML = '<p class="text-center" style="color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">Erro de conexão ao buscar seu progresso.</p>';
        });
}

function exibirDashboardSimplificado(data) {
    const container = document.getElementById('dashboard-content');
    
    // O HTML dos cards brancos é inserido aqui
    let html = `
        <div class="dashboard-simplificado">
            
            <div class="metricas-principais">
                <div class="metrica-card">
                    <div class="metrica-icon">📝</div>
                    <div class="metrica-info">
                        <h3>${data.metricas.total_simulados}</h3>
                        <p>Simulados Realizados</p>
                    </div>
                </div>
                <div class="metrica-card">
                    <div class="metrica-icon">🎯</div>
                    <div class="metrica-info">
                        <h3>${data.metricas.media_geral}%</h3>
                        <p>Média de Acertos</p>
                    </div>
                </div>
                <div class="metrica-card">
                    <div class="metrica-icon">✅</div>
                    <div class="metrica-info">
                        <h3>${data.metricas.total_acertos}</h3>
                        <p>Total de Acertos</p>
                    </div>
                </div>
                <div class="metrica-card">
                    <div class="metrica-icon">📚</div>
                    <div class="metrica-info">
                        <h3>${data.metricas.progresso_geral}%</h3>
                        <p>Progresso Geral</p>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>🚀 Progresso Rumo à Aprovação</h3>
                <div class="progresso-container-grande">
                    <div class="progresso-bar-grande" style="width: ${data.metricas.progresso_geral}%">
                        ${data.metricas.progresso_geral > 10 ? data.metricas.progresso_geral + '%' : ''}
                    </div>
                </div>
                <div class="progresso-info">
                    <span>Início</span>
                    <span>Meta: 100%</span>
                </div>
            </div>
    `;
    
    // Metas Ativas
    html += `
        <div class="card">
            <div class="card-header">
                <h3>🎯 Metas Ativas</h3>
                <button class="btn btn-primary" onclick="abrirModalMeta()">+ Nova Meta</button>
            </div>
    `;

    if (data.metas && data.metas.length > 0) {
        html += `<div class="metas-lista">`;
        data.metas.forEach(meta => {
            html += `
                <div class="meta-item">
                    <div class="meta-info">
                        <strong>${formatarTipoMeta(meta.tipo)}</strong>
                        <span>${meta.valor_atual}/${meta.valor_meta}</span>
                    </div>
                    <div class="progresso-meta">
                        <div class="progresso-bar-meta" style="width: ${meta.progresso}%"></div>
                    </div>
                    <span class="meta-percentual">${Math.round(meta.progresso)}%</span>
                </div>
            `;
        });
        html += `</div>`;
    } else {
        html += `
            <p class="text-center" style="padding: 20px; color: var(--text-light);">
                Nenhuma meta ativa. Crie sua primeira meta clicando no botão acima!
            </p>
        `;
    }
    html += `</div>`;
    
    // Áreas de Destaque
    if (data.areas_destaque && data.areas_destaque.length > 0) {
        html += `
            <div class="card">
                <h3>⭐ Áreas em Destaque (Melhor Desempenho)</h3>
                <div class="areas-destaque-lista">
        `;
        
        data.areas_destaque.forEach(area => {
            const classeDesempenho = area.percentual >= 70 ? 'desempenho-alto' : 
                                   area.percentual >= 50 ? 'desempenho-medio' : 'desempenho-baixo';
            html += `
                <div class="area-destaque-item">
                    <span class="area-nome">${area.area}</span>
                    <span class="area-percentual ${classeDesempenho}">
                        ${area.percentual}%
                    </span>
                </div>
            `;
        });
        
        html += `</div></div>`;
    }
    
    // Ações Rápidas
    html += `
        <div class="card">
            <h3>⚡ Ações Rápidas</h3>
            <div class="acoes-rapidas">
                <button class="btn-acao" onclick="iniciarRevisaoEspacada()">
                    <span class="acao-icon">🔄</span>
                    Revisão Espaçada (Erros)
                </button>
                <button class="btn-acao" onclick="navegarPara('tela-simulado')">
                    <span class="acao-icon">📝</span>
                    Novo Simulado
                </button>
                <button class="btn-acao" onclick="navegarPara('tela-redacao')">
                    <span class="acao-icon">✍️</span>
                    Praticar Redação
                </button>
            </div>
        </div>
    </div>
    
    <div id="modal-meta" class="modal hidden">
        <div class="modal-content">
            <div class="modal-header">
                <h3>🎯 Nova Meta</h3>
                <button class="btn-close" onclick="fecharModalMeta()">×</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label for="tipo-meta">Tipo de Meta:</label>
                    <select id="tipo-meta" class="form-control">
                        <option value="percentual_acerto">Percentual de Acerto</option>
                        <option value="questoes_resolvidas">Questões Resolvidas</option>
                        <option value="simulados_realizados">Simulados Realizados</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="valor-meta">Valor da Meta:</label>
                    <input type="number" id="valor-meta" class="form-control" placeholder="Ex: 80 (para % ou simulados)">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="fecharModalMeta()">Cancelar</button>
                <button class="btn btn-primary" onclick="criarMeta()">Criar Meta</button>
            </div>
        </div>
    </div>
    `;
    
    container.innerHTML = html;
}

function formatarTipoMeta(tipo) {
    const tipos = {
        'percentual_acerto': 'Média de Acerto',
        'questoes_resolvidas': 'Total de Questões Resolvidas', 
        'simulados_realizados': 'Total de Simulados Realizados',
        'tempo_estudo': 'Tempo de Estudo'
    };
    return tipos[tipo] || tipo;
}

function abrirModalMeta() {
    const modal = document.getElementById('modal-meta');
    if (modal) modal.classList.remove('hidden');
}

function fecharModalMeta() {
    const modal = document.getElementById('modal-meta');
    if (modal) modal.classList.add('hidden');
}

function criarMeta() {
    const tipo = document.getElementById('tipo-meta').value;
    const valor = document.getElementById('valor-meta').value;
    
    if (!valor || valor <= 0) {
        alert('Digite um valor válido para a meta!');
        return;
    }
    
    fetch('/api/dashboard/criar-meta', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({tipo: tipo, valor_meta: parseFloat(valor)})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            fecharModalMeta();
            carregarDashboardSimplificado(); // Recarrega o dashboard
            alert('Meta criada com sucesso!');
        } else {
            // (BUG CORRIGIDO) O 'a' extra foi removido daqui.
            alert('Erro: ' + data.error);
        }
    })
    .catch(error => {
        alert('Erro de conexão ao criar meta: ' + error.message);
    });
}

// ============================================================================
// 🔄 (NOVO) SISTEMA DE REVISÃO ESPAÇADA
// ============================================================================

function iniciarRevisaoEspacada() {
    // Mostra um feedback visual imediato
    const container = document.getElementById("dashboard-content");
    if (container) {
         container.innerHTML = '<div class="text-center"><div class="loading"></div><p style="color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">Buscando suas questões erradas para revisão...</p></div>';
    }

    fetch('/api/simulado/revisao-espacada', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`🎯 Revisão espaçada iniciada! \n\nEncontramos ${data.total_questoes} questões que você precisa revisar.\n\nVamos fortalecer seus pontos fracos! 🚀`);
            
            // Navega para a tela de simulado
            navegarPara('tela-simulado');

            // Inicia o simulado com os dados da revisão
            simuladoAtual = {
                indice_atual: data.indice_atual,
                total_questoes: data.total_questoes
            };
            mostrarTelaSimuladoAtivo(data.total_questoes);
            exibirQuestao(data.questao_atual, data.indice_atual, data.total_questoes, null);
            
            // (NOVO) Inicia o cronômetro para o simulado de revisão
            iniciarCronometro();

        } else {
            alert('❌ ' + data.error);
            // Volta para o dashboard se falhar
            carregarDashboardSimplificado();
        }
    })
    .catch(error => {
        alert('Erro ao iniciar revisão: ' + error.message);
        carregarDashboardSimplificado();
    });
}

// ============================================================================
// 📝 (NOVO) SISTEMA DE REDAÇÃO MELHORADO
// ============================================================================

function carregarTemasMelhorados() {
    fetch('/api/redacao/temas-melhorados')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const select = document.getElementById('temas-redacao');
            if (!select) return;
            
            select.innerHTML = '<option value="">Selecione um tema</option>';
            
            data.temas.forEach(tema => {
                const option = document.createElement('option');
                option.value = tema.titulo;
                option.textContent = tema.titulo;
                option.dataset.enunciado = tema.enunciado;
                option.dataset.textosBase = JSON.stringify(tema.textos_base || []);
                select.appendChild(option);
            });
            
            // Limpa o enunciado antigo se houver
            exibirEnunciadoRedacao(null, null);

            // Adiciona o listener de mudança
            select.removeEventListener('change', handleTemaChange); // Remove listener antigo
            select.addEventListener('change', handleTemaChange); // Adiciona novo
        }
    })
    .catch(error => {
        console.error('Erro ao carregar temas:', error);
    });
}

// (FUNÇÃO CORRIGIDA)
function handleTemaChange() {
    const select = document.getElementById('temas-redacao');
    if (!select) return;
    const selectedOption = select.options[select.selectedIndex];
    
    if (!selectedOption || !selectedOption.value) {
        exibirEnunciadoRedacao(null, null); // Limpa se selecionar "Selecione um tema"
        return;
    }
    const enunciado = selectedOption.dataset.enunciado;
    const textosBase = JSON.parse(selectedOption.dataset.textosBase || '[]');
    exibirEnunciadoRedacao(enunciado, textosBase);
}

// (FUNÇÃO CORRIGIDA)
function exibirEnunciadoRedacao(enunciado, textosBase) {
    let container = document.getElementById('enunciado-redacao-container');
    const editorCard = document.querySelector('.redacao-editor .card');

    if (!container) {
        container = document.createElement('div');
        container.id = 'enunciado-redacao-container';
        container.className = 'card enunciado-redacao'; // Adiciona classe 'card'
        
        // Insere antes do grupo do textarea
        const formGroupTextarea = document.querySelector('#texto-redacao').parentNode;
        if (editorCard && formGroupTextarea) {
            editorCard.insertBefore(container, formGroupTextarea);
        }
    }

    // Se o enunciado for nulo, oculta o container
    if (!enunciado) {
        container.innerHTML = '';
        container.classList.add('hidden');
        return;
    }
    
    container.classList.remove('hidden');
    let html = `<h4>📋 Enunciado da Proposta</h4><div class="enunciado-texto">${enunciado}</div>`;
    
    if (textosBase && textosBase.length > 0) {
        html += '<h5>📚 Textos de Apoio:</h5><ul class="textos-apoio">';
        textosBase.forEach(texto => {
            html += `<li>${texto}</li>`;
        });
        html += '</ul>';
    }
    
    container.innerHTML = html;
}

function corrigirRedacaoGeminiReal() {
    const temaSelect = document.getElementById('temas-redacao');
    const textoRedacao = document.getElementById('texto-redacao').value;
    
    if (!temaSelect.value) {
        alert('Selecione um tema!');
        return;
    }
    
    const selectedOption = temaSelect.options[temaSelect.selectedIndex];
    const enunciado = selectedOption.dataset.enunciado;
    
    if (textoRedacao.trim().length < 100) {
        alert('Digite uma redação com pelo menos 100 caracteres para uma análise justa.');
        return;
    }
    
    const btnCorrigir = document.getElementById('btn-corrigir');
    const textoOriginal = btnCorrigir ? btnCorrigir.innerHTML : "🔍 Corrigir com IA";
    if(btnCorrigir) {
        btnCorrigir.innerHTML = '<span class="loading small"></span> Corrigindo com IA...';
        btnCorrigir.disabled = true;
    }
    
    // Limpa o resultado anterior
    const resultadoDiv = document.getElementById('resultado-correcao');
    if (resultadoDiv) resultadoDiv.classList.add('hidden');

    fetch('/api/redacao/corrigir-gemini-real', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            tema: temaSelect.value,
            texto: textoRedacao,
            enunciado: enunciado
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            exibirCorrecaoRedacaoAvancada(data.correcao);
        } else {
            alert('Erro ao corrigir: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro de conexão ao corrigir redação.');
    })
    .finally(() => {
        if(btnCorrigir) {
            btnCorrigir.innerHTML = textoOriginal;
            btnCorrigir.disabled = false;
        }
    });
}

function exibirCorrecaoRedacaoAvancada(correcao) {
    const resultadoDiv = document.getElementById('resultado-correcao');
    if (!resultadoDiv) return;

    let html = `
        <div class="card resultado-header">
            <div class="nota-container">
                <h3>📊 Resultado da Correção - ENEM</h3>
                <div class="nota-final">${correcao.nota_final}/1000</div>
                <div class="nota-descricao">
                    ${correcao.nota_final >= 800 ? '🎉 Excelente! Nível competitivo!' :
                      correcao.nota_final >= 600 ? '👍 Bom desempenho! Continue evoluindo!' : 
                      '📚 Precisa de mais prática. Foco nos estudos!'}
                </div>
            </div>
        </div>
        
        <div class="card">
            <h4>📈 Análise por Competências ENEM:</h4>
    `;
    
    if (correcao.competencias && Array.isArray(correcao.competencias)) {
        correcao.competencias.forEach(comp => {
            const nota = comp.nota || 0;
            const percentual = (nota / 200) * 100;
            html += `
                <div class="competencia-item">
                    <div class="competencia-header">
                        <h5>${comp.nome || "Competência"}</h5>
                        <span class="nota-competencia">${nota}/200</span>
                    </div>
                    <div class="progress-bar-competencia">
                        <div class="progress-fill" style="width: ${percentual}%"></div>
                    </div>
                    <p class="comentario-competencia">${comp.comentario || "Sem comentário."}</p>
                </div>
            `;
        });
    }
    
    html += `</div>`;
    
    // Pontos fortes e fracos
    html += `
        <div class="analise-grid">
            <div class="card">
                <h4>✅ Pontos Fortes:</h4>
                <ul class="lista-pontos">
    `;
    
    if (correcao.pontos_fortes && correcao.pontos_fortes.length > 0) {
        correcao.pontos_fortes.forEach(ponto => {
            html += `<li>${ponto}</li>`;
        });
    } else {
        html += '<li>Continue desenvolvendo suas habilidades</li>';
    }
    
    html += `
                </ul>
            </div>
            <div class="card">
                <h4>📝 Pontos a Melhorar:</h4>
                <ul class="lista-pontos">
    `;
    
    if (correcao.pontos_fracos && correcao.pontos_fracos.length > 0) {
        correcao.pontos_fracos.forEach(ponto => {
            html += `<li>${ponto}</li>`;
        });
    } else {
        html += '<li>Ótimo trabalho! Mantenha o foco</li>';
    }
    
    html += `
                </ul>
            </div>
        </div>
        
        <div class="card">
            <h4>💡 Sugestões de Melhoria:</h4>
            <ul class="lista-pontos">
    `;
    
    if (correcao.sugestoes_melhoria && correcao.sugestoes_melhoria.length > 0) {
        correcao.sugestoes_melhoria.forEach(sugestao => {
            html += `<li>${sugestao}</li>`;
        });
    } else {
        html += '<li>Continue praticando regularmente</li>';
    }
    
    html += `
            </ul>
        </div>
    `;
    
    resultadoDiv.innerHTML = html;
    resultadoDiv.classList.remove("hidden");
    resultadoDiv.scrollIntoView({ behavior: "smooth" });
}

// ============================================================================
// 🔄 (NOVO) ATUALIZAR FUNÇÕES EXISTENTES
// ============================================================================

// (SOBRESCRITO) - Sobrescrever a função de navegação para usar o novo dashboard
const navegarParaOriginal = navegarPara;
navegarPara = function(tela) {
    // Chama a função original
    navegarParaOriginal(tela); 
    
    // Adiciona a nova lógica
    if (tela === 'tela-dashboard') {
        // Usar o novo dashboard simplificado
        carregarDashboardSimplificado();
    } 
    // A lógica de redação já foi atualizada dentro da função original
}

// (SOBRESCRITO) - Atualizar função de correção de redação
// A função original foi mantida, mas a nova função 'corrigirRedacaoGeminiReal'
// será chamada pelo botão no index.html (que já foi corrigido para chamar 'corrigirRedacao()')
// Vamos garantir que 'corrigirRedacao()' chame a nova.
const corrigirRedacaoOriginal = corrigirRedacao;
corrigirRedacao = function() {
    corrigirRedacaoGeminiReal(); // Garante que o clique no botão chame a função REAL
};