// Máscaras dos campos brasileiros: CPF, CNPJ, telefone e CEP.
// O campo escolhe a máscara pelo atributo data-mask (ver accounts/fields.py).
// Aqui só formatamos enquanto a pessoa digita: quem valida é o servidor.

// Troca cada "#" do padrão pelo próximo caractere digitado.
// Para no fim do que foi digitado, para o apagar (Backspace) funcionar normalmente.
function applyPattern(chars, pattern) {
    let result = '';
    let next = 0;
    for (const symbol of pattern) {
        if (next >= chars.length) {
            break;
        }
        if (symbol === '#') {
            result += chars[next];
            next += 1;
        } else {
            result += symbol;
        }
    }
    return result;
}

const MASKS = {
    cpf(value) {
        const digits = value.replace(/\D/g, '');
        return applyPattern(digits, '###.###.###-##');
    },

    cnpj(value) {
        // Desde 2026 o CNPJ pode ter letras nas 12 primeiras posições.
        const chars = value.toUpperCase().replace(/[^0-9A-Z]/g, '');
        return applyPattern(chars, '##.###.###/####-##');
    },

    cep(value) {
        const digits = value.replace(/\D/g, '');
        return applyPattern(digits, '#####-###');
    },

    phone(value) {
        let digits = value.replace(/\D/g, '');
        // O preenchimento automático do navegador costuma colocar +55 na frente.
        if (digits.length > 11 && digits.startsWith('55')) {
            digits = digits.slice(2);
        }
        // Fixo tem 10 números; celular tem 11.
        const pattern = digits.length > 10 ? '(##) #####-####' : '(##) ####-####';
        return applyPattern(digits, pattern);
    },
};

document.querySelectorAll('[data-mask]').forEach((input) => {
    const mask = MASKS[input.dataset.mask];
    input.addEventListener('input', () => {
        input.value = mask(input.value);
    });
});
