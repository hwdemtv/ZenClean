(function() {
    'use strict';

    console.log('ZenClean Script Loading...');

    // ==================== 1. 立即注入全局函数 (确保 HTML 内联点击立刻有效) ====================
    window.openDownloadModal = function() {
        const modal = document.getElementById('downloadModal');
        if (modal) {
            modal.style.display = 'flex';
            modal.setAttribute('aria-hidden', 'false');
        }
    };

    window.closeDownloadModal = function() {
        const modal = document.getElementById('downloadModal');
        if (modal) {
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        }
    };

    window.openDisclaimerModal = function() {
        const modal = document.getElementById('disclaimerModal');
        if (modal) {
            modal.style.display = 'flex';
            modal.setAttribute('aria-hidden', 'false');
        }
    };

    window.closeDisclaimerModal = function() {
        const modal = document.getElementById('disclaimerModal');
        if (modal) {
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        }
    };

    window.openContactModal = function() {
        const modal = document.getElementById('contactModal');
        if (modal) {
            modal.style.display = 'flex';
            modal.setAttribute('aria-hidden', 'false');
        }
    };

    window.closeContactModal = function() {
        const modal = document.getElementById('contactModal');
        if (modal) {
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        }
    };

    window.toggleTheme = function() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        
        if (next === 'light') {
            document.body.classList.add('light-mode');
        } else {
            document.body.classList.remove('light-mode');
        }
    };

    window.scrollToTop = function() {
        window.scrollTo({top: 0, behavior: 'smooth'});
    };

    // ==================== 2. 核心初始化逻辑 ====================
    function initScrollReveal() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale, .reveal-text, .reveal-subtext').forEach(el => {
            observer.observe(el);
        });
    }

    function initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        if (savedTheme === 'light') {
            document.body.classList.add('light-mode');
        }

        const toggle = document.querySelector('.theme-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => {
                // 主题切换已通过 window.toggleTheme 处理，此处只需确保事件绑定
            });
        }
    }

    function initFaq() {
        const faqQuestions = document.querySelectorAll('.faq-question');
        faqQuestions.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const item = btn.parentElement;
                item.classList.toggle('active');
            });
        });
    }

    function initFaqFilter() {
        const navBtns = document.querySelectorAll('.faq-nav-btn');
        if (navBtns.length === 0) return;

        navBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                navBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const category = btn.dataset.category;
                const faqItems = document.querySelectorAll('.faq-item');
                
                faqItems.forEach(item => {
                    const itemCat = item.dataset.category;
                    if (category === 'all' || itemCat === category) {
                        item.style.display = '';
                    } else {
                        item.style.display = 'none';
                    }
                });
            });
        });
    }

    function initFloatBtn() {
        const floatBtn = document.getElementById('floatDownload');
        if (!floatBtn) return;
        window.addEventListener('scroll', () => {
            if (window.scrollY > 300) {
                floatBtn.classList.add('visible');
            } else {
                floatBtn.classList.remove('visible');
            }
        });
    }

    function initCounter() {
        const counter = document.getElementById('totalStorage');
        if (!counter) return;

        const targetStr = counter.innerText.replace(/,/g, '');
        const target = parseInt(targetStr);
        if (isNaN(target)) return;

        const duration = 2000;
        let startTime = null;

        function animate(timestamp) {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            counter.innerText = Math.floor(progress * target).toLocaleString();
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        }

        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                requestAnimationFrame(animate);
                observer.disconnect();
            }
        }, { threshold: 0.5 });
        observer.observe(counter);
    }

    // ==================== 3. 鲁棒性初始化加载 ====================
    function runAllInits() {
        initScrollReveal();
        initTheme();
        initFaq();
        initFaqFilter();
        initFloatBtn();
        initCounter();

        // 弹窗点击背景关闭
        document.querySelectorAll('.modal-overlay').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                    modal.setAttribute('aria-hidden', 'true');
                }
            });
        });

        console.log('ZenClean Init Success v2.0');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', runAllInits);
    } else {
        runAllInits();
    }

})();